import os
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from typing import Optional


def generate_key() -> bytes:
    """Generate a new Fernet key"""
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_data(data: str, key: bytes) -> str:
    """Encrypt string data using Fernet"""
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """Decrypt string data using Fernet"""
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_data.encode())
    return decrypted.decode()


def load_master_key(key_file: Path) -> bytes:
    """Load master key from file, create if doesn't exist"""
    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = generate_key()
        save_master_key(key, key_file)
        return key


def save_master_key(key: bytes, key_file: Path) -> None:
    """Save master key to file with secure permissions"""
    key_file.parent.mkdir(parents=True, exist_ok=True)
    with open(key_file, 'wb') as f:
        f.write(key)
    # Set restrictive permissions (owner only)
    os.chmod(key_file, 0o600)


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash


def generate_salt() -> bytes:
    """Generate random salt"""
    return os.urandom(16)


def obfuscate_api_key(api_key: str, show_chars: int = 4) -> str:
    """Obfuscate API key for display purposes"""
    if len(api_key) <= show_chars:
        return "*" * len(api_key)
    return api_key[:2] + "*" * (len(api_key) - show_chars) + api_key[-show_chars:]