import os
import base64
import uuid
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes


def generate_salt():
    """Generate a cryptographically secure random salt"""
    return os.urandom(16)


def encode_id(uuid_id):
    """Encode UUID to URL-safe base64 string"""
    if isinstance(uuid_id, str):
        uuid_id = uuid.UUID(uuid_id)
    # Convert UUID to bytes and encode as URL-safe base64
    uuid_bytes = uuid_id.bytes
    encoded = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=').decode('ascii')
    return encoded


def decode_id(encoded_id):
    """Decode URL-safe base64 string to UUID"""
    # Add padding if needed
    padding = 4 - (len(encoded_id) % 4)
    if padding != 4:
        encoded_id += '=' * padding

    try:
        uuid_bytes = base64.urlsafe_b64decode(encoded_id)
        return uuid.UUID(bytes=uuid_bytes)
    except (ValueError, Exception):
        return None


def passphrase_to_key(passphrase, salt):
    """
    Derive encryption key from passphrase using PBKDF2.
    CRITICAL: Uses unique salt per secret (not shared SECRET_KEY).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # Increased from 100k for better security (OWASP 2023 recommendation)
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))
    return key


def encrypt(data, passphrase, salt):
    """
    Encrypt data with passphrase using unique salt.
    Returns base64-encoded string (for storage in TextField).
    """
    key = passphrase_to_key(passphrase, salt)
    plain = data.encode('utf-8')
    encrypted_bytes = Fernet(key).encrypt(plain)
    # Encode as base64 string for TextField storage
    return base64.b64encode(encrypted_bytes).decode('ascii')


def decrypt(token, passphrase, salt):
    """
    Decrypt token with passphrase using the provided salt.
    Returns decrypted string (not bytes).
    """
    key = passphrase_to_key(passphrase, salt)

    # Decode from base64 string to bytes
    if isinstance(token, str):
        token = base64.b64decode(token.encode('ascii'))

    decrypted_bytes = Fernet(key).decrypt(token)
    # Decode bytes to string before returning
    return decrypted_bytes.decode('utf-8')
