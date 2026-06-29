from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from motor.motor_asyncio import AsyncIOMotorDatabase

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger

log = get_logger("db.external_directory_secrets")


def _get_fernet() -> Fernet:
    """Retrieve the Fernet cipher using the configured encryption key.

    Raises:
        ValueError: If `EXTERNAL_DIRECTORY_ENCRYPTION_KEY` is not set or invalid.
    """
    key_secret = settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY
    if not key_secret:
        raise ValueError(
            "EXTERNAL_DIRECTORY_ENCRYPTION_KEY is required to manage external directory secrets. "
            "Please configure it."
        )

    key_value = key_secret.get_secret_value()
    try:
        return Fernet(key_value.encode("utf-8"))
    except Exception as e:
        raise ValueError(f"EXTERNAL_DIRECTORY_ENCRYPTION_KEY is invalid: {str(e)}") from e


async def store_secret_uri(db: AsyncIOMotorDatabase, raw_uri: str) -> None:
    """Encrypt and store the raw connection URI in the database.

    Raises:
        ValueError: If the encryption key is not configured.
    """
    fernet = _get_fernet()
    encrypted_uri = fernet.encrypt(raw_uri.encode("utf-8"))

    await db.external_directory_secrets.update_one(
        {"_id": "singleton"},
        {"$set": {"encrypted_uri": encrypted_uri}},
        upsert=True,
    )


async def resolve_secret_uri(db: AsyncIOMotorDatabase) -> str | None:
    """Retrieve and decrypt the raw connection URI from the database.

    Returns:
        The decrypted URI string, or None if no secret is stored.

    Raises:
        ValueError: If the encryption key is not configured or fails to decrypt.
    """
    doc = await db.external_directory_secrets.find_one({"_id": "singleton"})
    if not doc or "encrypted_uri" not in doc:
        return None

    encrypted_uri: bytes = doc["encrypted_uri"]
    fernet = _get_fernet()

    try:
        return fernet.decrypt(encrypted_uri).decode("utf-8")
    except InvalidToken as e:
        log.error("external_directory.decrypt_failed", reason="Invalid token")
        raise ValueError("Failed to decrypt the external directory URI. Is the key correct?") from e
    except Exception as e:
        log.error("external_directory.decrypt_failed", error=str(e))
        raise ValueError(f"Failed to decrypt external directory URI: {str(e)}") from e
