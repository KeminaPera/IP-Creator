"""
Encryption utilities for secure storage of sensitive data.

Uses Fernet symmetric encryption for API keys and other
sensitive configuration values.
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from app.config.settings import settings


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Uses Fernet symmetric encryption with a master key derived
    from the application's ENCRYPTION_KEY setting.
    """
    
    def __init__(self):
        """Initialize encryption service with master key."""
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """
        Create Fernet instance from encryption key.
        
        Derives a proper Fernet key from the application's
        ENCRYPTION_KEY using PBKDF2 with a deterministic salt
        derived from the key itself.
        """
        key = settings.ENCRYPTION_KEY.encode()
        
        # If key is already a valid Fernet key (32 url-safe base64 bytes)
        if len(key) == 44:  # Base64 encoded 32 bytes
            try:
                base64.urlsafe_b64decode(key)
                return Fernet(key)
            except Exception as e:
                # Log but continue with key derivation
                from app.utils.logger import logger
                logger.warning(f"Invalid Fernet key format, will derive: {e}")
        
        # Derive key using PBKDF2 with deterministic salt from key hash
        # This ensures same key always produces same derived key
        import hashlib
        salt = hashlib.sha256(key).digest()[:16]  # Use first 16 bytes of key hash as salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(derived_key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return data
        encrypted = self._fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string value.
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted plain text
        """
        if not encrypted_data:
            return encrypted_data
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception:
            # Fallback: if decryption fails, return the raw value.
            # This handles cases where the encryption key was changed
            # but the database still contains values encrypted with the old key.
            # In production, re-encrypt all values after key rotation.
            return encrypted_data
    
    def mask_sensitive(self, data: str, visible_chars: int = 4) -> str:
        """
        Mask sensitive data for display purposes.
        
        Args:
            data: Original sensitive data
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked string (e.g., "****abcd")
        """
        if not data or len(data) <= visible_chars:
            return "****"
        return "*" * (len(data) - visible_chars) + data[-visible_chars:]


# Global encryption service instance
encryption_service = EncryptionService()
