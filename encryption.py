"""
AES-256 encryption utilities for sensitive voter data.
Uses Fernet symmetric encryption from the cryptography library.
"""

import base64
import hashlib
from cryptography.fernet import Fernet


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from a secret string using SHA-256."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class DataEncryptor:
    """Encrypt and decrypt sensitive fields like Aadhaar numbers and vote data."""

    def __init__(self, key: str):
        self._fernet = Fernet(_derive_key(key))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return plaintext."""
        if not ciphertext:
            return ""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def hash_value(self, value: str) -> str:
        """Create a one-way SHA-256 hash (for lookups without decryption)."""
        return hashlib.sha256(value.encode()).hexdigest()
