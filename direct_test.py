#!/usr/bin/env python3
"""
Direct test of encryption functionality without external dependencies.
"""

import base64
import hashlib

def test_simple_encryption():
    """Test a simple encryption approach using built-in Python libraries"""

    print("Testing simple encryption approach...")

    # Simple salt for demonstration
    salt = b"chat_app_salt_1234567890"

    # Test password
    password = "secret123"

    # Derive key using PBKDF2
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, 32)
    print(f"Derived key (32 bytes): {key}")

    # Convert to URL-safe base64 for use with Fernet-like encryption
    key_b64 = base64.urlsafe_b64encode(key)
    print(f"Base64 encoded key: {key_b64}")

    # Test simple XOR encryption (demonstration only)
    message = "Hello, this is a test message!"
    print(f"Original message: {message}")

    # XOR with key
    key_bytes = base64.urlsafe_b64decode(key_b64)

    # Pad message to be multiple of key length
    message_bytes = message.encode()
    padded_message = message_bytes + b'\x00' * (len(key_bytes) - len(message_bytes) % len(key_bytes))

    # XOR with key
    encrypted = bytearray()
    for i, byte in enumerate(padded_message):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])

    print(f"Encrypted (bytes): {bytes(encrypted)}")

    # XOR again to decrypt
    decrypted = bytearray()
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ key_bytes[i % len(key_bytes)])

    # Remove padding and decode
    decrypted_message = bytes(decrypted).rstrip(b'\x00').decode()
    print(f"Decrypted message: {decrypted_message}")

    if message == decrypted_message:
        print("✓ SUCCESS: Encryption/Decryption works!")
        return True
    else:
        print("✗ FAILURE: Messages don't match")
        return False

if __name__ == "__main__":
    test_simple_encryption()