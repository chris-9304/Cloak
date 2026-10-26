#!/usr/bin/env python3
"""
Simple command-line chat application to test core functionality.
"""

import sys
import os
import threading
import time
from encryption import EncryptionManager

class SimpleChat:
    def __init__(self):
        self.encryption = EncryptionManager()
        self.username = ""
        self.password = ""

    def set_username(self, name):
        """Set the user's display name"""
        self.username = name
        print(f"Username set to: {self.username}")

    def set_password(self, password):
        """Set the encryption password"""
        self.password = password
        if self.encryption.set_password(password):
            print("Encryption enabled")
            return True
        else:
            print("Failed to set encryption password")
            return False

    def encrypt_and_send(self, message):
        """Encrypt and prepare a message for sending"""
        try:
            encrypted = self.encryption.encrypt_message(message)
            return encrypted
        except Exception as e:
            print(f"Error encrypting message: {e}")
            return None

    def decrypt_and_receive(self, encrypted_message):
        """Decrypt and process a received message"""
        try:
            decrypted = self.encryption.decrypt_message(encrypted_message)
            return decrypted
        except Exception as e:
            print(f"Error decrypting message: {e}")
            return None

    def simulate_chat(self):
        """Simulate a simple chat session"""
        print("=== Simple Encrypted Chat Demo ===")
        print("This demonstrates the core encryption functionality")
        print()

        # Set up chat
        self.set_username("Alice")
        self.set_password("secret123")

        # Test message
        test_message = "Hello, this is a test encrypted message!"
        print(f"Original message: {test_message}")

        # Encrypt
        encrypted = self.encrypt_and_send(test_message)
        if encrypted:
            print(f"Encrypted message: {encrypted}")

            # Decrypt
            decrypted = self.decrypt_and_receive(encrypted)
            if decrypted:
                print(f"Decrypted message: {decrypted}")

                if test_message == decrypted:
                    print("✓ Message encryption/decryption successful!")
                else:
                    print("✗ Message mismatch - encryption/decryption failed")
            else:
                print("✗ Failed to decrypt message")
        else:
            print("✗ Failed to encrypt message")

def main():
    chat = SimpleChat()
    chat.simulate_chat()

if __name__ == "__main__":
    main()