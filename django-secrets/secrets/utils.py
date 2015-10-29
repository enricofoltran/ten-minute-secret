import os, struct, base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from django.conf import settings


KNUTH_PRIME = getattr(settings, 'SECRET_KNUTH_PRIME', 1580030173)
KNUTH_INVERSE = getattr(settings, 'SECRET_KNUTH_INVERSE', 59260789)
KNUTH_RANDOM = getattr(settings, 'SECRET_KNUTH_RANDOM', 1163945558)
KNUTH_MAX_INT = getattr(settings, 'SECRET_KNUTH_MAX_INT', 2147483647)


def knuth_encode(uid):
    oid = ((uid * KNUTH_PRIME) & KNUTH_MAX_INT) ^ KNUTH_RANDOM
    return base64.urlsafe_b64encode(struct.pack('!L', oid))[:6]


def knuth_decode(oid):
    padded = (oid + "==").encode('utf-8')
    decoded = struct.unpack('!L', base64.urlsafe_b64decode(padded))[0]
    uid = ((decoded ^ KNUTH_RANDOM) * KNUTH_INVERSE) & KNUTH_MAX_INT
    return uid


def passphrase_to_key(passphrase):
    salt = settings.SECRET_KEY.encode('utf-8')
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))
    return key


def encrypt(data, passphrase):
    key = passphrase_to_key(passphrase)
    plain = data.encode('utf-8')
    return Fernet(key).encrypt(plain)


def decrypt(token, passphrase):
    key = passphrase_to_key(passphrase)
    secret = token.encode('utf-8')
    return Fernet(key).decrypt(secret)
