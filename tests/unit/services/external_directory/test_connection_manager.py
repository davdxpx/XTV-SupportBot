from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from xtv_support.services.external_directory.connection_manager import ExternalConnectionManager
from xtv_support.services.external_directory.connection_manager import (
    test_connection as run_test_connection,
)


@pytest.mark.asyncio
async def test_reconfigure_closes_old_client():
    manager = ExternalConnectionManager()

    with patch(
        "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient"
    ) as mock_motor:
        mock_client = MagicMock()
        mock_motor.return_value = mock_client

        await manager.get_client("old_uri")
        assert manager.is_connected()

        # Reconfigure
        await manager.reconfigure("new_uri")

        # Ensure old client was closed
        mock_client.close.assert_called_once()

        # Old client isn't completely cleared yet if we immediately get it, but let's just make sure get_client creates a new one
        await manager.get_client("new_uri")
        assert mock_motor.call_count == 2


@pytest.mark.asyncio
async def test_connection_test_success():
    with patch(
        "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient"
    ) as mock_motor:
        mock_client = MagicMock()
        mock_motor.return_value = mock_client
        mock_client.__getitem__.return_value.command = AsyncMock()
        mock_client.__getitem__.return_value.__getitem__.return_value.count_documents = AsyncMock(
            return_value=1
        )

        success, msg = await run_test_connection("uri", "db", "coll")
        assert success is True
        assert msg == "ok"
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_connection_empty_collection():
    with patch(
        "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient"
    ) as mock_motor:
        mock_client = MagicMock()
        mock_motor.return_value = mock_client
        mock_client.__getitem__.return_value.command = AsyncMock()
        mock_client.__getitem__.return_value.__getitem__.return_value.count_documents = AsyncMock(
            return_value=0
        )

        success, msg = await run_test_connection("uri", "db", "coll")
        assert success is True
        assert "empty" in msg


@pytest.mark.asyncio
async def test_connection_auth_failure():
    with patch(
        "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient"
    ) as mock_motor:
        mock_client = MagicMock()
        mock_motor.return_value = mock_client

        mock_client.__getitem__.return_value.command = AsyncMock(
            side_effect=OperationFailure("auth failed", code=18)
        )

        success, msg = await run_test_connection("uri", "db", "coll")
        assert success is False
        assert "Authentication failed" in msg


@pytest.mark.asyncio
async def test_connection_timeout():
    with patch(
        "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient"
    ) as mock_motor:
        mock_client = MagicMock()
        mock_motor.return_value = mock_client

        mock_client.__getitem__.return_value.command = AsyncMock(
            side_effect=ServerSelectionTimeoutError("timeout")
        )

        success, msg = await run_test_connection("uri", "db", "coll")
        assert success is False
        assert "timed out" in msg
