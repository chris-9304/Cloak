#!/usr/bin/env python3
"""
Encryption module for encrypted chat application.
Handles message encryption and decryption using Fernet.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets

class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None

    def set_password(self, password: str) -> bool:
        """Set the encryption password and generate key"""
        if not password:
            return False

        try:
            # Generate a salt (in a real app, this should be stored securely)
            salt = b"chat_app_salt_1234567890"  # This is for demonstration only

            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

            self.key = key
            self.cipher = Fernet(key)
            return True
        except Exception as e:
            print(f"Error setting password: {e}")
            return False

    def encrypt_message(self, message: str) -> bytes:
        """Encrypt a message"""
        if not self.cipher:
            raise Exception("No encryption key set")

        return self.cipher.encrypt(message.encode())

    def decrypt_message(self, encrypted_message: bytes) -> str:
        """Decrypt a message"""
        if not self.cipher:
            raise Exception("No encryption key set")

        return self.cipher.decrypt(encrypted_message).decode()

    def generate_key(self) -> str:
        """Generate a new key (for testing purposes)"""
        return Fernet.generate_key().decode()

# Example usage (for testing)
if __name__ == "__main__":
    # Test the encryption manager
    em = EncryptionManager()

    # Set a password
    if em.set_password("my_secret_password"):
        print("Encryption key generated successfully")

        # Test encryption/decryption
        original_message = "Hello, this is a secret message!"
        encrypted = em.encrypt_message(original_message)
        decrypted = em.decrypt_message(encrypted)

        print(f"Original: {original_message}")
        print(f"Encrypted: {encrypted}")
        print(f"Decrypted: {decrypted}")
    else:
        print("Failed to set password")