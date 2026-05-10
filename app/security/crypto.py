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
        ENCRYPTION_KEY using PBKDF2 if needed.
        """
        key = settings.ENCRYPTION_KEY.encode()
        
        # If key is already a valid Fernet key (32 url-safe base64 bytes)
        if len(key) == 44:  # Base64 encoded 32 bytes
            try:
                base64.urlsafe_b64decode(key)
                return Fernet(key)
            except Exception:
                pass
        
        # Otherwise, derive key using PBKDF2
        salt = b"ip-creator-fixed-salt"  # In production, use random salt and store it
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
        decrypted = self._fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
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
