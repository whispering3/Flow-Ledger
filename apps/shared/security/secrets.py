import secrets

from cryptography.fernet import Fernet

from apps.api.config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().secrets_encryption_key.encode("utf-8"))


def generate_signing_secret() -> str:
    return secrets.token_urlsafe(32)


def encrypt_secret(raw_secret: str) -> str:
    return _fernet().encrypt(raw_secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def generate_encrypted_signing_secret() -> str:
    return encrypt_secret(generate_signing_secret())
