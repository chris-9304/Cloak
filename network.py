#!/usr/bin/env python3
"""
Network communication module for encrypted peer-to-peer chat.

Provides:
  • UDP broadcast-based peer *discovery*  (announce + listen + manual scan)
  • TCP connection management  (connect, accept, send, receive)
  • Length-prefixed message framing  (4-byte big-endian header)

All public callbacks are fired on background threads – the caller is
responsible for marshalling onto the GUI thread (e.g. via root.after()).
"""

import json
import socket
import struct
import threading
import time
from typing import Callable, Optional


# ── Constants ───────────────────────────────────────────────────────
DISCOVERY_PORT = 5000          # UDP port for broadcast beacons
DEFAULT_TCP_PORT = 5001        # Default TCP port for chat messages
BROADCAST_INTERVAL = 3         # seconds between discovery beacons
BUFFER_SIZE = 65536
MAX_FRAME_SIZE = 1024 * 1024


# ── helpers ─────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    """Best-effort detection of this machine's LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from *sock* or raise."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed")
        buf += chunk
    return buf


# ── Discovery (UDP) ────────────────────────────────────────────────

class DiscoveryService:
    """Announces this peer and listens for others via UDP broadcast.

    Supports a manual ``scan()`` that fires an immediate burst of broadcasts
    so peers are discovered faster.
    """

    def __init__(
        self,
        username: str,
        tcp_port: int = DEFAULT_TCP_PORT,
        discovery_port: int = DISCOVERY_PORT,
        on_peer_found: Optional[Callable] = None,
    ):
        self.username = username
        self.tcp_port = tcp_port
        self.discovery_port = discovery_port
        self.local_ip = _get_local_ip()
        self.on_peer_found = on_peer_found   # callback(name, ip, port)
        self._running = False
        self._broadcast_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._listen_sock = None
        self.on_error = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._running = True
        self._stop_event.clear()
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        for sock in (self._listen_sock, self._broadcast_sock):
            if sock:
                sock.close()

    def update_username(self, name: str) -> None:
        self.username = name

    def scan(self) -> None:
        """Send an immediate burst of discovery beacons (3 rapid-fire)."""
        def _burst():
            for _ in range(3):
                if self._running:
                    self._send_beacon()
                self._stop_event.wait(0.3)
        threading.Thread(target=_burst, daemon=True).start()

    # ── internals ───────────────────────────────────────────────────

    def _make_payload(self) -> bytes:
        return json.dumps({
            "type": "discovery",
            "name": self.username,
            "ip": self.local_ip,
            "port": self.tcp_port,
        }).encode()

    def _send_beacon(self) -> None:
        with self._lock:
            try:
                if self._broadcast_sock is None:
                    self._broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except (AttributeError, OSError):
                        pass
                self._broadcast_sock.sendto(self._make_payload(), ("<broadcast>", self.discovery_port))
            except Exception:
                self._broadcast_sock = None

    def _broadcast_loop(self) -> None:
        while self._running:
            self._send_beacon()
            self._stop_event.wait(BROADCAST_INTERVAL)
        with self._lock:
            if self._broadcast_sock:
                try:
                    self._broadcast_sock.close()
                except Exception:
                    pass
                self._broadcast_sock = None

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        self._listen_sock = sock
        try:
            sock.bind(("", self.discovery_port))
        except OSError as exc:
            sock.close()
            if self.on_error:
                self.on_error(f"Discovery unavailable: {exc}. Use direct connection.")
            return
        sock.settimeout(2)
        while self._running:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                if msg.get("type") != "discovery":
                    continue
                peer_ip = addr[0]
                peer_port = msg["port"]
                peer_name = msg["name"]
                if (not isinstance(peer_name, str) or not 1 <= len(peer_name) <= 64
                        or type(peer_port) is not int or not 1 <= peer_port <= 65535):
                    continue
                # Ignore our own broadcasts (compare ip AND port)
                if peer_ip == self.local_ip and peer_port == self.tcp_port:
                    continue
                if self.on_peer_found:
                    self.on_peer_found(peer_name, peer_ip, peer_port)
            except socket.timeout:
                continue
            except Exception:
                continue
        sock.close()


# ── TCP Chat Connection ────────────────────────────────────────────

class ChatConnection:
    """Manages a single TCP connection for exchanging chat messages.

    Messages are framed as:
        [4-byte big-endian length][payload bytes]
    Payload is a JSON envelope: {"type": ..., "data": ...}
    """

    MSG_CHAT = "chat"
    MSG_HANDSHAKE = "handshake"
    MSG_DISCONNECT = "disconnect"

    def __init__(
        self,
        on_message: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
    ):
        self.sock: Optional[socket.socket] = None
        self.on_message = on_message          # callback(msg_type, data_dict)
        self.on_disconnect = on_disconnect    # callback()
        self._running = False
        self._send_lock = threading.Lock()
        self._disconnected_fired = False

    # ── outgoing connection ─────────────────────────────────────────

    def connect(self, host: str, port: int) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
            self._running = True
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[ChatConnection] connect failed: {e}")
            self.sock = None
            return False

    # ── accept an incoming connection ───────────────────────────────

    def accept(self, client_sock: socket.socket) -> None:
        self.sock = client_sock
        self._running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

    # ── sending ─────────────────────────────────────────────────────

    def send(self, msg_type: str, data: dict) -> bool:
        if not self.sock or not self._running:
            return False
        with self._send_lock:
            try:
                payload = json.dumps({"type": msg_type, "data": data}).encode()
                if len(payload) > MAX_FRAME_SIZE:
                    return False
                header = struct.pack("!I", len(payload))
                self.sock.sendall(header + payload)
                return True
            except Exception as e:
                print(f"[ChatConnection] send error: {e}")
                return False

    # ── receiving ───────────────────────────────────────────────────

    def _recv_loop(self) -> None:
        try:
            while self._running and self.sock:
                header = _recv_exact(self.sock, 4)
                length = struct.unpack("!I", header)[0]
                if not 0 < length <= MAX_FRAME_SIZE:
                    break
                payload = _recv_exact(self.sock, length)
                envelope = json.loads(payload.decode())
                if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
                    break
                msg_type = envelope.get("type", "")
                data = envelope.get("data", {})
                if msg_type == self.MSG_DISCONNECT:
                    break
                if self.on_message:
                    self.on_message(msg_type, data)
        except (ConnectionError, OSError, ValueError, UnicodeError, AttributeError):
            pass
        finally:
            self.close()
            self._fire_disconnect()

    # ── teardown ────────────────────────────────────────────────────

    def _fire_disconnect(self) -> None:
        """Fire the on_disconnect callback exactly once."""
        if not self._disconnected_fired:
            self._disconnected_fired = True
            if self.on_disconnect:
                self.on_disconnect()

    def close(self) -> None:
        self._running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    @property
    def is_alive(self) -> bool:
        return self._running and self.sock is not None


# ── TCP Listener ────────────────────────────────────────────────────

class TCPListener:
    """Listens for incoming TCP connections on a given port."""

    def __init__(self, port: int, on_accept: Callable):
        self.port = port
        self.on_accept = on_accept       # callback(client_socket, address)
        self._server: Optional[socket.socket] = None
        self._running = False

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("0.0.0.0", self.port))
        self._server.listen(5)
        self._server.settimeout(2)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client, addr = self._server.accept()
                self.on_accept(client, addr)
            except socket.timeout:
                continue
            except OSError:
                break


# ── quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Local IP: {_get_local_ip()}")
    print("NetworkManager modules loaded OK")
