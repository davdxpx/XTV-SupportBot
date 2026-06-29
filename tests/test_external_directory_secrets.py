import pytest
from mongomock_motor import AsyncMongoMockClient
from pydantic import SecretStr

from xtv_support.config.settings import settings
from xtv_support.infrastructure.db.external_directory_secrets import (
    resolve_secret_uri,
    store_secret_uri,
)


@pytest.mark.asyncio
async def test_secret_storage_round_trip():
    # Setup mock key
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = SecretStr(
        "2xXwF_Z-83_n4fB3m-1Yw7JqXhR6T3h-mZ5A8ZtB2t0="
    )

    client = AsyncMongoMockClient()
    db = client.test_db

    raw_uri = "mongodb://user:pass@external:27017/db"

    # Store
    await store_secret_uri(db, raw_uri)

    # Verify encrypted in DB
    doc = await db.external_directory_secrets.find_one({"_id": "singleton"})
    assert doc is not None
    assert doc["encrypted_uri"] != raw_uri
    assert isinstance(doc["encrypted_uri"], bytes)

    # Resolve
    resolved = await resolve_secret_uri(db)
    assert resolved == raw_uri


@pytest.mark.asyncio
async def test_secret_storage_missing_key_raises():
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = None
    client = AsyncMongoMockClient()
    db = client.test_db

    with pytest.raises(ValueError, match="EXTERNAL_DIRECTORY_ENCRYPTION_KEY is required"):
        await store_secret_uri(db, "mongodb://test")


@pytest.mark.asyncio
async def test_secret_resolve_invalid_key_raises():
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = SecretStr(
        "2xXwF_Z-83_n4fB3m-1Yw7JqXhR6T3h-mZ5A8ZtB2t0="
    )
    client = AsyncMongoMockClient()
    db = client.test_db

    await store_secret_uri(db, "mongodb://test")

    # Corrupt key
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = SecretStr(
        "invalid_key_that_is_long_enough_but_wrong_base64="
    )

    with pytest.raises(ValueError, match="EXTERNAL_DIRECTORY_ENCRYPTION_KEY is invalid"):
        await resolve_secret_uri(db)
