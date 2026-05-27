"""AES-256-GCM encryption utilities for OAuth token storage.

Provides symmetric encryption/decryption using AES-256-GCM with random nonces.
The encrypted output format is: base64(nonce || ciphertext || tag) where the
nonce is 12 bytes and the authentication tag is 16 bytes.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoUtils:
    """AES-256-GCM encryption for OAuth tokens.

    Uses a 32-byte key (provided as base64-encoded string) to encrypt and
    decrypt sensitive data such as Google OAuth tokens before database storage.

    Args:
        encryption_key_b64: Base64-encoded 32-byte AES-256 key.

    Raises:
        ValueError: If the decoded key is not exactly 32 bytes.
    """

    _NONCE_SIZE = 12
    _TAG_SIZE = 16

    def __init__(self, encryption_key_b64: str) -> None:
        """Initialize CryptoUtils with a base64-encoded encryption key.

        Args:
            encryption_key_b64: Base64-encoded 32-byte AES-256 key.

        Raises:
            ValueError: If the decoded key is not exactly 32 bytes.
        """
        key_bytes = base64.b64decode(encryption_key_b64)
        if len(key_bytes) != 32:
            raise ValueError(f"Encryption key must be exactly 32 bytes, got {len(key_bytes)} bytes")
        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM with a random nonce.

        Generates a cryptographically random 12-byte nonce, encrypts the
        plaintext, and returns the combined result as a base64-encoded string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded string containing nonce + ciphertext + tag.
        """
        nonce = os.urandom(self._NONCE_SIZE)
        plaintext_bytes = plaintext.encode("utf-8")
        # AESGCM.encrypt returns ciphertext + tag (tag is appended)
        ciphertext_and_tag = self._aesgcm.encrypt(nonce, plaintext_bytes, None)
        # Output format: nonce || ciphertext || tag
        combined = nonce + ciphertext_and_tag
        return base64.b64encode(combined).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded AES-256-GCM ciphertext.

        Decodes the base64 input, extracts the nonce (first 12 bytes),
        ciphertext, and authentication tag (last 16 bytes), then decrypts.

        Args:
            ciphertext: Base64-encoded string containing nonce + ciphertext + tag.

        Returns:
            The decrypted plaintext string.

        Raises:
            cryptography.exceptions.InvalidTag: If the ciphertext was tampered
                with or the wrong key is used.
            ValueError: If the input is too short to contain nonce + tag.
        """
        combined = base64.b64decode(ciphertext)
        if len(combined) < self._NONCE_SIZE + self._TAG_SIZE:
            raise ValueError(
                f"Ciphertext too short: expected at least "
                f"{self._NONCE_SIZE + self._TAG_SIZE} bytes, got {len(combined)}"
            )
        nonce = combined[: self._NONCE_SIZE]
        ciphertext_and_tag = combined[self._NONCE_SIZE :]
        # AESGCM.decrypt expects ciphertext + tag concatenated
        plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext_and_tag, None)
        return plaintext_bytes.decode("utf-8")
