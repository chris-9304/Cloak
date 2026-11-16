"""Versioned password-confirmed sessions, independent of the Tkinter interface."""
import secrets
import threading
from encryption import EncryptionManager
from network import ChatConnection


class SecureSession:
    VERSION = 2

    def __init__(self, password, name, post, timeout=8):
        self.password, self.name, self.post = password, name, post
        self.cipher = EncryptionManager()
        self.peer_cipher = None
        self.challenge = secrets.token_hex(32)
        self.peer_name = "Peer"
        self.peer_challenge = None
        self.ready = False
        self.closed = False
        self.hello_received = False
        self.transport = ChatConnection(self._message, self._disconnected)
        self.timer = threading.Timer(timeout, lambda: self.fail("Password verification timed out"))
        self.timer.daemon = True
        self._lock = threading.RLock()

    def start(self, host=None, port=None, client=None):
        if not self.cipher.set_password(self.password):
            self.fail("Could not derive encryption key")
            return
        if self.closed:
            if client:
                client.close()
            return
        # Send hello before starting receive, preventing proof/hello reordering.
        import socket
        try:
            sock = client or socket.create_connection((host, port), timeout=5)
            sock.settimeout(None)
            with self._lock:
                if self.closed:
                    sock.close()
                    return
                self.transport.sock = sock
                self.transport._running = True
                if not self.transport.send("hello", {
                    "version": self.VERSION, "name": self.name,
                    "salt": self.cipher.get_salt().hex(), "challenge": self.challenge,
                }):
                    raise ConnectionError("Handshake send failed")
                self.timer.start()
                threading.Thread(target=self.transport._recv_loop, daemon=True).start()
        except (OSError, ConnectionError) as exc:
            self.fail(f"Connection failed: {exc}")

    def _message(self, kind, data):
        try:
            if kind == "hello":
                if self.hello_received or data.get("version") != self.VERSION:
                    raise ValueError("Incompatible or repeated handshake; both peers need CLOAK v2")
                salt = bytes.fromhex(data["salt"])
                challenge = data["challenge"]
                name = data["name"]
                if len(salt) != 16 or not isinstance(challenge, str) or len(challenge) != 64:
                    raise ValueError("Invalid handshake")
                if not isinstance(name, str) or not 1 <= len(name) <= 64:
                    raise ValueError("Invalid callsign")
                if salt == self.cipher.get_salt() or challenge == self.challenge:
                    raise ValueError("Reflected handshake rejected")
                self.peer_challenge = challenge
                self.hello_received = True
                self.peer_name = name
                self.peer_cipher = EncryptionManager()
                self.peer_cipher.set_password(self.password, salt)
                self.transport.send("proof", {"cipher": self.peer_cipher.encrypt_message("CLOAK-v2-proof:" + challenge + ":" + self.challenge).decode()})
            elif kind == "proof":
                if not self.hello_received or self.ready:
                    raise ValueError("Unexpected password proof")
                proof = self.cipher.try_decrypt(data["cipher"].encode())
                expected = "CLOAK-v2-proof:" + self.challenge + ":" + self.peer_challenge
                if proof != expected:
                    raise ValueError("Passphrase mismatch: password verification failed")
                with self._lock:
                    if self.closed:
                        return
                    self.ready = True
                    self.timer.cancel()
                    self.password = ""
                    self.post("ready", self.peer_name)
            elif kind == "chat":
                if not self.ready:
                    raise ValueError("Message arrived before password verification")
                message = self.peer_cipher.try_decrypt(data["cipher"].encode())
                if message is None:
                    raise ValueError("Message authentication failed")
                self.post("message", (self.peer_name, message))
            else:
                raise ValueError("Unsupported protocol message")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self.fail(str(exc))

    def send(self, message):
        return self.ready and not self.closed and self.transport.send(
            "chat", {"cipher": self.cipher.encrypt_message(message).decode()})

    def fail(self, reason):
        with self._lock:
            if self.closed:
                return
            self.close()
            self.post("error", reason)

    def _disconnected(self):
        self.fail("Peer disconnected")

    def close(self):
        with self._lock:
            self.closed = True
            self.ready = False
            self.password = ""
            self.timer.cancel()
            self.transport.close()
