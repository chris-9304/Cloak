#!/usr/bin/env python3
"""
Simple Encrypted Chat Demo - No GUI Required

This script demonstrates the core functionality of our encrypted chat application
using only built-in Python libraries. It focuses on the encryption and messaging
functionality without GUI dependencies.
"""

import sys
import os
import base64
import hashlib
import secrets

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SimpleEncryptionManager:
    """Simple encryption manager using built-in libraries"""

    def __init__(self):
        self.key = None
        self.salt = b"chat_app_salt_1234567890"  # Fixed salt for demo purposes

    def set_password(self, password: str) -> bool:
        """Set the encryption password and generate key using PBKDF2"""
        if not password:
            return False

        try:
            # Derive key from password using PBKDF2
            # In a real app, you'd want to use a random salt and store it securely
            key = hashlib.pbkdf2_hmac('sha256', password.encode(), self.salt, 100000, 32)
            # Convert to URL-safe base64 for use with Fernet-like encryption
            self.key = base64.urlsafe_b64encode(key)
            return True
        except Exception as e:
            print(f"Error setting password: {e}")
            return False

    def encrypt_message(self, message: str) -> bytes:
        """Encrypt a message using XOR with key"""
        if not self.key:
            raise Exception("No encryption key set")

        # Simple XOR encryption for demonstration
        # In a real implementation, you'd use proper encryption like Fernet
        key_bytes = base64.urlsafe_b64decode(self.key)

        # Pad message to be multiple of key length
        message_bytes = message.encode()
        padded_message = message_bytes + b'\x00' * (len(key_bytes) - len(message_bytes) % len(key_bytes))

        # XOR with key
        encrypted = bytearray()
        for i, byte in enumerate(padded_message):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])

        return bytes(encrypted)

    def decrypt_message(self, encrypted_message: bytes) -> str:
        """Decrypt a message using XOR with key"""
        if not self.key:
            raise Exception("No encryption key set")

        # XOR with key again (XOR is symmetric)
        key_bytes = base64.urlsafe_b64decode(self.key)

        # XOR with key
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_message):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])

        # Remove padding and decode
        return bytes(decrypted).rstrip(b'\x00').decode()

class SimpleChatDemo:
    def __init__(self):
        self.encryption = SimpleEncryptionManager()
        self.username = ""
        self.is_encrypted = False

    def set_username(self):
        """Set the user's display name"""
        while not self.username:
            self.username = input("Enter your name: ").strip()
            if not self.username:
                print("Name cannot be empty. Please try again.")

    def set_password(self):
        """Set the encryption password"""
        while not self.is_encrypted:
            password = input("Enter encryption password: ")

            if not password:
                print("Password cannot be empty. Please try again.")
                continue

            if self.encryption.set_password(password):
                self.is_encrypted = True
                print("✓ Encryption enabled successfully!")
                return True
            else:
                print("✗ Failed to set encryption password. Please try again.")

        return False

    def demo_encryption(self):
        """Run a simple encryption/decryption demo"""
        print("\n=== ENCRYPTION DEMO ===")

        # Test message
        test_message = "This is a secret message for demonstration!"
        print(f"Original message: {test_message}")

        # Encrypt
        encrypted = self.encryption.encrypt_message(test_message)
        if encrypted:
            print(f"Encrypted message (bytes): {encrypted}")
            print(f"Encrypted message (base64): {base64.urlsafe_b64encode(encrypted).decode()}")

            # Decrypt
            decrypted = self.encryption.decrypt_message(encrypted)
            if decrypted:
                print(f"Decrypted message: {decrypted}")

                if test_message == decrypted:
                    print("✓ SUCCESS - Message encryption/decryption works correctly!")
                    return True
                else:
                    print("✗ FAILURE - Messages don't match!")
                    return False
            else:
                print("✗ FAILED - Could not decrypt message")
                return False
        else:
            print("✗ FAILED - Could not encrypt message")
            return False

    def run_demo(self):
        """Run the complete demo"""
        print("🔐 Simple Encrypted Chat Demo")
        print("=" * 40)

        # Set up user
        self.set_username()
        print(f"Hello, {self.username}!")

        # Set up encryption
        if self.set_password():
            print("🔐 Encryption is now active")

            # Run encryption demo
            success = self.demo_encryption()

            if success:
                print("\n🎉 All encryption features are working correctly!")
                print("The core encryption functionality is demonstrated above.")
            else:
                print("\n❌ Encryption demo failed!")
        else:
            print("❌ Failed to set up encryption")

def main():
    try:
        demo = SimpleChatDemo()
        demo.run_demo()
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()