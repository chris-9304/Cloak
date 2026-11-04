#!/usr/bin/env python3
"""
Encryption module for encrypted chat application.
Handles message encryption and decryption using Fernet with shared-key exchange.

Both peers must use the SAME password. A shared salt is transmitted during the
handshake so both sides derive an identical Fernet key.
"""

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets


class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None
        self.salt = None

    # ── key derivation ──────────────────────────────────────────────

    def set_password(self, password: str, salt: bytes | None = None) -> bool:
        """Derive a Fernet key from *password* + *salt*.

        If *salt* is None a fresh 16-byte random salt is generated (caller
        should transmit it to the peer).  When *salt* is provided (received
        from the peer) the same key is re-derived deterministically.
        """
        if not password:
            return False
        try:
            self.salt = salt if salt else secrets.token_bytes(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100_000,
            )
            self.key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.cipher = Fernet(self.key)
            return True
        except Exception as e:
            print(f"Error setting password: {e}")
            return False

    def get_salt(self) -> bytes:
        """Return the salt used for key derivation."""
        return self.salt

    # ── encrypt / decrypt ───────────────────────────────────────────

    def encrypt_message(self, message: str) -> bytes:
        """Encrypt a plaintext message and return cipher-bytes."""
        if not self.cipher:
            raise RuntimeError("No encryption key set – call set_password first")
        return self.cipher.encrypt(message.encode())

    def decrypt_message(self, encrypted_message: bytes) -> str:
        """Decrypt cipher-bytes back to a plaintext string."""
        if not self.cipher:
            raise RuntimeError("No encryption key set – call set_password first")
        return self.cipher.decrypt(encrypted_message).decode()

    def try_decrypt(self, encrypted_message: bytes) -> str | None:
        """Attempt decryption; return None instead of raising on failure."""
        try:
            return self.decrypt_message(encrypted_message)
        except (InvalidToken, Exception):
            return None


# ── quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    em = EncryptionManager()
    if em.set_password("my_secret_password"):
        print("✓ Key generated")
        original = "Hello, this is a secret message!"
        encrypted = em.encrypt_message(original)
        decrypted = em.decrypt_message(encrypted)
        print(f"  Original : {original}")
        print(f"  Encrypted: {encrypted[:60]}…")
        print(f"  Decrypted: {decrypted}")
        assert original == decrypted, "round-trip failed!"
        print("✓ Round-trip OK")

        # Verify shared-salt derivation
        em2 = EncryptionManager()
        em2.set_password("my_secret_password", salt=em.get_salt())
        assert em2.decrypt_message(encrypted) == original
        print("✓ Shared-salt derivation OK")
