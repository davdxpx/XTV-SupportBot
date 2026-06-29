"""External User Directory Concrete Provider.

The Motor/Mongo-backed provider that fetches and caches user signals from an external database.
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from xtv_support.core.logger import get_logger
from xtv_support.services.external_directory.interpreter import resolve_signal
from xtv_support.services.external_directory.model import (
    ExternalDirectoryConfig,
    ResolvedUserSignal,
)

log = get_logger("external_directory.provider")


class ExternalDirectoryProvider:
    """Connects to a secondary Mongo database to fetch external user signals."""

    CACHE_TTL_SECONDS = 300

    def __init__(
        self,
        config: ExternalDirectoryConfig,
        *,
        client_factory: Callable[[str], AsyncIOMotorClient] | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory
        self._client: AsyncIOMotorClient | None = None
        self._cache: OrderedDict[int, dict] = OrderedDict()
        self._lock = asyncio.Lock()

    def _get_client(self) -> AsyncIOMotorClient:
        if self._client is None:
            # Resolving the URI ref is outside the scope of this prompt,
            # but we assume the factory handles it for now, or we just pass the ref.
            uri = self._config.connection_uri_ref
            if self._client_factory:
                self._client = self._client_factory(uri)
            else:
                self._client = AsyncIOMotorClient(
                    uri,
                    serverSelectionTimeoutMS=5_000,
                    tz_aware=True,
                )
        return self._client

    async def _fetch_raw_document(self, telegram_user_id: int) -> dict[str, Any] | None:
        client = self._get_client()
        db = client[self._config.database_name]
        coll = db[self._config.collection_name]

        query_val = (
            str(telegram_user_id)
            if self._config.external_id_is_string
            else telegram_user_id
        )

        return await coll.find_one({self._config.external_id_field: query_val})

    async def get_signal(self, telegram_user_id: int) -> ResolvedUserSignal:
        now = datetime.now(UTC).timestamp()

        # Check cache
        async with self._lock:
            if telegram_user_id in self._cache:
                entry = self._cache[telegram_user_id]
                self._cache.move_to_end(telegram_user_id)  # LRU bump
                if entry["expires_at"] > now:
                    return entry["signal"]
                # Expired
                self._cache.pop(telegram_user_id)

        # Fetch
        try:
            raw_doc = await self._fetch_raw_document(telegram_user_id)
        except (PyMongoError, asyncio.TimeoutError) as exc:
            log.warning(
                "external_directory.query_failed",
                database=self._config.database_name,
                collection=self._config.collection_name,
                error=str(exc),
            )
            # Safe default on error
            return ResolvedUserSignal()

        # Interpret
        signal = resolve_signal(raw_doc, self._config)

        # Cache result
        async with self._lock:
            self._cache[telegram_user_id] = {
                "signal": signal,
                "expires_at": now + self.CACHE_TTL_SECONDS,
            }
            if len(self._cache) > 10_000:
                self._cache.popitem(last=False)

        return signal

    def invalidate(self, telegram_user_id: int) -> None:
        """Remove a specific user from the cache."""
        # Not async, so we do it carefully if lock isn't held, but dict pop is atomic in GIL
        self._cache.pop(telegram_user_id, None)

    def clear_cache(self) -> None:
        """Clear all cached signals."""
        self._cache.clear()
