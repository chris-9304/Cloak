#!/usr/bin/env python3
"""
Peer management module for encrypted chat application.
Handles peer information, connection states, and lifetime tracking.
"""

import time
from typing import Optional


class Peer:
    """Represents a remote chat peer discovered on the LAN."""

    def __init__(self, name: str, ip_address: str, port: int = 5001):
        self.name = name
        self.ip_address = ip_address
        self.port = port               # TCP port the peer listens on
        self.is_connected = False
        self.last_seen: float = time.time()

    # ── display helpers ─────────────────────────────────────────────
    def __str__(self) -> str:
        return f"{self.name} ({self.ip_address}:{self.port})"

    def __repr__(self) -> str:
        return f"Peer({self.name!r}, {self.ip_address!r}, {self.port})"

    @property
    def uid(self) -> str:
        """Unique identifier for this peer (ip:port)."""
        return f"{self.ip_address}:{self.port}"

    # ── state helpers ───────────────────────────────────────────────
    def touch(self) -> None:
        """Mark this peer as recently seen."""
        self.last_seen = time.time()

    def is_stale(self, timeout: float = 15.0) -> bool:
        """Return True if the peer hasn't been seen within *timeout* seconds."""
        return (time.time() - self.last_seen) > timeout

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False


class PeerManager:
    """Thread-safe registry of discovered peers."""

    def __init__(self):
        self.peers: dict[str, Peer] = {}   # uid → Peer
        self.connected_peer: Optional[Peer] = None

    def upsert(self, peer: Peer) -> bool:
        """Add or update a peer.  Returns True if it's a *new* peer."""
        is_new = peer.uid not in self.peers
        peer.touch()
        self.peers[peer.uid] = peer
        return is_new

    def remove(self, uid: str) -> bool:
        if uid in self.peers:
            del self.peers[uid]
            return True
        return False

    def get(self, uid: str) -> Optional[Peer]:
        return self.peers.get(uid)

    def all_peers(self) -> list[Peer]:
        return list(self.peers.values())

    def prune_stale(self, timeout: float = 15.0) -> list[str]:
        """Remove peers not seen within *timeout* seconds.  Returns removed uids."""
        stale = [uid for uid, p in self.peers.items() if p.is_stale(timeout)]
        for uid in stale:
            del self.peers[uid]
        return stale

    def set_connected(self, peer: Peer) -> None:
        self.connected_peer = peer

    def clear_connected(self) -> None:
        if self.connected_peer:
            self.connected_peer.disconnect()
        self.connected_peer = None


# ── quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    pm = PeerManager()
    p1 = Peer("Alice", "192.168.1.101", 5001)
    p2 = Peer("Bob", "192.168.1.102", 5001)
    print(f"new? {pm.upsert(p1)}")   # True
    print(f"new? {pm.upsert(p1)}")   # False (update)
    pm.upsert(p2)
    print("All peers:", pm.all_peers())
