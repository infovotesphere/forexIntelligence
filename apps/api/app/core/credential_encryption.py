from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class CredentialEncryptionError(ValueError):
    pass


def _fernet() -> Fernet:
    key = get_settings().mt5_encryption_key
    if not key:
        raise CredentialEncryptionError("MT5_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError("MT5_ENCRYPTION_KEY is invalid") from exc


def encrypt_credentials(value: bytes) -> str:
    return _fernet().encrypt(value).decode("ascii")


def decrypt_credentials(value: str) -> bytes:
    try:
        return _fernet().decrypt(value.encode("ascii"))
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError("Stored MT5 credentials cannot be decrypted") from exc
