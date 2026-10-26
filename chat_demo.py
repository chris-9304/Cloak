#!/usr/bin/env python3
"""
Encrypted Chat Application - Core Functionality Demo

This script demonstrates the complete encryption functionality without GUI dependencies.
It shows how encryption/decryption works in a real chat scenario.
"""

import sys
import os
import getpass

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption import EncryptionManager

class ChatDemo:
    def __init__(self):
        self.encryption = EncryptionManager()
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
            # Use getpass to hide password input
            password = getpass.getpass("Enter encryption password: ")

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

    def encrypt_message(self, message):
        """Encrypt a message"""
        try:
            return self.encryption.encrypt_message(message)
        except Exception as e:
            print(f"✗ Error encrypting message: {e}")
            return None

    def decrypt_message(self, encrypted_message):
        """Decrypt a message"""
        try:
            return self.encryption.decrypt_message(encrypted_message)
        except Exception as e:
            print(f"✗ Error decrypting message: {e}")
            return None

    def demo_encryption(self):
        """Run a complete encryption/decryption demo"""
        print("\n=== ENCRYPTION DEMO ===")

        # Test message
        test_message = "This is a secret message for demonstration!"
        print(f"Original message: {test_message}")

        # Encrypt
        encrypted = self.encrypt_message(test_message)
        if encrypted:
            print(f"Encrypted message: {encrypted.decode('utf-8')[:50]}...")

            # Decrypt
            decrypted = self.decrypt_message(encrypted)
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

    def interactive_chat(self):
        """Run an interactive chat session"""
        if not self.is_encrypted:
            print("Encryption not enabled. Please set a password first.")
            return

        print("\n=== INTERACTIVE CHAT DEMO ===")
        print("Type 'quit' to exit the chat")
        print("Type 'demo' to run encryption demo again")
        print("Messages will be encrypted before sending")
        print("-" * 50)

        while True:
            try:
                message = input(f"\n{self.username}: ")

                if message.lower() == 'quit':
                    print("Exiting chat...")
                    break
                elif message.lower() == 'demo':
                    self.demo_encryption()
                    continue
                elif not message.strip():
                    continue

                # Encrypt the message
                encrypted = self.encrypt_message(message)
                if encrypted:
                    print(f"✓ Message encrypted and ready to send")
                    print(f"  Encrypted: {encrypted.decode('utf-8')[:50]}...")

                    # For demo purposes, we'll also show what would be received
                    decrypted = self.decrypt_message(encrypted)
                    print(f"  Would be received as: {decrypted}")
                else:
                    print("✗ Failed to encrypt message")

            except KeyboardInterrupt:
                print("\n\nExiting chat...")
                break
            except EOFError:
                print("\n\nExiting chat...")
                break

    def run_demo(self):
        """Run the complete demo"""
        print("🔐 Encrypted Chat Application - Core Demo")
        print("=" * 50)

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
                print("Ready for interactive chat mode...")

                # Start interactive chat
                self.interactive_chat()
            else:
                print("\n❌ Encryption demo failed!")
        else:
            print("❌ Failed to set up encryption")

def main():
    try:
        demo = ChatDemo()
        demo.run_demo()
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()