#!/usr/bin/env python3
"""
Network communication module for encrypted chat application.
Handles TCP connections and message framing.
"""

import socket
import threading
import json
import time
from typing import Optional, Tuple
import struct

class NetworkManager:
    def __init__(self):
        self.socket = None
        self.is_connected = False
        self.receive_thread = None

    def connect_to_peer(self, host: str, port: int) -> bool:
        """Connect to a peer at the specified host and port"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout
            self.socket.connect((host, port))
            self.is_connected = True

            # Start receiving messages in a separate thread
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def listen_for_peers(self, port: int) -> bool:
        """Listen for incoming connections on the specified port"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', port))
            self.socket.listen(5)

            # Start accepting connections in a separate thread
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()

            return True
        except Exception as e:
            print(f"Failed to start listening: {e}")
            return False

    def _accept_connections(self):
        """Accept incoming connections"""
        while self.socket:
            try:
                client_socket, address = self.socket.accept()
                print(f"Connection from {address}")
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.socket:
                    print(f"Error accepting connection: {e}")
                break

    def _handle_client(self, client_socket):
        """Handle communication with a connected client"""
        try:
            while self.is_connected:
                # Receive message length
                length_data = client_socket.recv(4)
                if not length_data:
                    break

                message_length = struct.unpack('!I', length_data)[0]

                # Receive the actual message
                message_data = client_socket.recv(message_length)
                if not message_data:
                    break

                # Process the received message
                self._process_message(message_data)

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def _receive_messages(self):
        """Receive messages from the connected peer"""
        try:
            while self.is_connected and self.socket:
                # Receive message length
                length_data = self.socket.recv(4)
                if not length_data:
                    break

                message_length = struct.unpack('!I', length_data)[0]

                # Receive the actual message
                message_data = self.socket.recv(message_length)
                if not message_data:
                    break

                # Process the received message
                self._process_message(message_data)

        except Exception as e:
            print(f"Error receiving messages: {e}")
        finally:
            self.is_connected = False

    def _process_message(self, message_data: bytes):
        """Process a received message"""
        try:
            # In a real implementation, this would decrypt and handle the message
            print(f"Received message: {message_data}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def send_message(self, message: bytes) -> bool:
        """Send a message to the connected peer"""
        if not self.is_connected or not self.socket:
            return False

        try:
            # Frame the message: [4-byte length][message data]
            message_length = len(message)
            framed_message = struct.pack('!I', message_length) + message

            self.socket.sendall(framed_message)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from the peer"""
        self.is_connected = False
        if self.socket:
            self.socket.close()
            self.socket = None

# Example usage (for testing)
if __name__ == "__main__":
    # Test the network manager
    nm = NetworkManager()

    # This would be used in the main application to handle connections
    print("NetworkManager initialized")