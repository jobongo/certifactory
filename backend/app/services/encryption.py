import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(master_key: str) -> bytes:
    return hashlib.sha256(master_key.encode()).digest()


def encrypt_private_key(plaintext: str, master_key: str) -> str:
    key = _derive_key(master_key)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_private_key(encrypted: str, master_key: str) -> str:
    key = _derive_key(master_key)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
