from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import (
    ConfigurationError,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from xtv_support.core.logger import get_logger

log = get_logger("external_directory.connection")


class ExternalConnectionManager:
    """Manages a single, lazily-created Motor client for the external directory.

    This is intentionally a separate client from the bot's main database, with
    shorter timeouts to prevent slow external directories from blocking bot operations.
    """

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._lock = asyncio.Lock()
        self._raw_uri: str | None = None

    async def get_client(self, raw_uri: str) -> AsyncIOMotorClient:
        """Returns the active client, creating it if necessary."""
        async with self._lock:
            if self._client is not None and self._raw_uri == raw_uri:
                return self._client

            # Close old if URI changed
            if self._client is not None:
                self._client.close()
                self._client = None

            self._raw_uri = raw_uri
            self._client = AsyncIOMotorClient(
                raw_uri,
                maxPoolSize=10,
                minPoolSize=1,
                serverSelectionTimeoutMS=4000,
                tz_aware=True,
            )
            return self._client

    async def reconfigure(self, new_raw_uri: str) -> None:
        """Closes any existing connection and prepares to use a new one."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
            self._raw_uri = new_raw_uri

    async def close(self) -> None:
        """Closes the client connection."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
            self._raw_uri = None

    def is_connected(self) -> bool:
        """Returns True if a client is currently active (not necessarily reachable)."""
        return self._client is not None


async def test_connection(
    raw_uri: str, database_name: str, collection_name: str, *, timeout_seconds: float = 4.0
) -> tuple[bool, str]:
    """Tests if an external MongoDB connection is reachable and valid.

    This opens a short-lived connection and attempts a ping and a single document read.

    Returns:
        (success, human_readable_message)
    """
    client = None
    try:
        # Create an isolated client for the test
        client = AsyncIOMotorClient(
            raw_uri,
            serverSelectionTimeoutMS=int(timeout_seconds * 1000),
            tz_aware=True,
        )

        # 1. Ping the server
        db = client[database_name]
        await db.command("ping")

        # 2. Check the collection
        coll = db[collection_name]
        doc_count = await coll.count_documents({}, limit=1)

        if doc_count == 0:
            return (
                True,
                f"connected, but the collection '{collection_name}' is empty — confirm the collection name is correct",
            )

        return True, "ok"

    except ServerSelectionTimeoutError as e:
        log.warning("external_directory.test.timeout", error=str(e))
        return False, "Connection timed out. Check the URI and ensure the database is reachable."
    except OperationFailure as e:
        # Code 18 is Authentication failed
        log.warning("external_directory.test.operation_failure", error=str(e))
        if e.code == 18:
            return False, "Authentication failed. Check your username and password."
        return False, f"Database error: {e.details.get('errmsg', str(e))}"
    except ConfigurationError as e:
        log.warning("external_directory.test.config_error", error=str(e))
        return False, f"Configuration error: {str(e)}. The URI format might be invalid."
    except PyMongoError as e:
        log.warning("external_directory.test.pymongo_error", error=str(e))
        return False, f"MongoDB error: {str(e)}"
    except Exception as e:
        log.error("external_directory.test.unknown_error", error=str(e))
        return False, f"Unexpected error: {str(e)}"
    finally:
        if client:
            client.close()
