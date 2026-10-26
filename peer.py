#!/usr/bin/env python3
"""
Peer management module for encrypted chat application.
Handles peer information and connection states.
"""

import socket
from typing import Optional

class Peer:
    def __init__(self, name: str, ip_address: str, port: int = 8080):
        self.name = name
        self.ip_address = ip_address
        self.port = port
        self.is_connected = False
        self.connection_time = None

    def __str__(self):
        return f"{self.ip_address} - {self.name}"

    def connect(self) -> bool:
        """Attempt to connect to this peer"""
        # In a real implementation, this would establish a TCP connection
        # For now, we'll just set the connection state
        self.is_connected = True
        return True

    def disconnect(self):
        """Disconnect from this peer"""
        self.is_connected = False
        self.connection_time = None

    def is_reachable(self) -> bool:
        """Check if this peer is reachable"""
        # In a real implementation, this would ping the peer or attempt connection
        # For now, we'll assume peers are reachable
        return True

class PeerManager:
    def __init__(self):
        self.peers = {}
        self.connected_peer = None

    def add_peer(self, peer: Peer) -> bool:
        """Add a peer to the manager"""
        if peer.ip_address in self.peers:
            return False

        self.peers[peer.ip_address] = peer
        return True

    def remove_peer(self, ip_address: str) -> bool:
        """Remove a peer from the manager"""
        if ip_address in self.peers:
            del self.peers[ip_address]
            return True
        return False

    def get_peer(self, ip_address: str) -> Optional[Peer]:
        """Get a peer by IP address"""
        return self.peers.get(ip_address)

    def get_all_peers(self) -> list:
        """Get all peers"""
        return list(self.peers.values())

    def get_connected_peer(self) -> Optional[Peer]:
        """Get the currently connected peer"""
        return self.connected_peer

    def set_connected_peer(self, peer: Peer) -> bool:
        """Set the currently connected peer"""
        if peer.is_connected:
            self.connected_peer = peer
            return True
        return False

    def clear_connections(self):
        """Clear all peer connections"""
        for peer in self.peers.values():
            peer.disconnect()
        self.connected_peer = None

# Example usage (for testing)
if __name__ == "__main__":
    # Test the peer manager
    pm = PeerManager()

    # Add some peers
    peer1 = Peer("Alice", "192.168.1.101", 8080)
    peer2 = Peer("Bob", "192.168.1.102", 8080)

    pm.add_peer(peer1)
    pm.add_peer(peer2)

    print("All peers:")
    for peer in pm.get_all_peers():
        print(f"  {peer}")

    # Connect to a peer
    if pm.set_connected_peer(peer1):
        print(f"Connected to {pm.get_connected_peer()}")
    else:
        print("Failed to connect to peer")