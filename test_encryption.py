#!/usr/bin/env python3
"""
Simple test for encryption module without GUI dependencies.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption import EncryptionManager

def test_encryption():
    """Test the encryption functionality"""
    print("Testing encryption module...")

    # Create encryption manager
    em = EncryptionManager()

    # Test setting password
    if em.set_password("my_secret_password"):
        print("✓ Password set successfully")
    else:
        print("✗ Failed to set password")
        return False

    # Test encryption/decryption
    original_message = "Hello, this is a secret message!"
    try:
        encrypted = em.encrypt_message(original_message)
        decrypted = em.decrypt_message(encrypted)

        print(f"✓ Original: {original_message}")
        print(f"✓ Encrypted: {encrypted}")
        print(f"✓ Decrypted: {decrypted}")

        if original_message == decrypted:
            print("✓ Encryption/Decryption test PASSED")
            return True
        else:
            print("✗ Encryption/Decryption test FAILED - messages don't match")
            return False

    except Exception as e:
        print(f"✗ Encryption/Decryption test FAILED - {e}")
        return False

if __name__ == "__main__":
    success = test_encryption()
    sys.exit(0 if success else 1)