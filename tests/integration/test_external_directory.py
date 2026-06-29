from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from mongomock_motor import AsyncMongoMockClient
from pydantic import SecretStr

from xtv_support.config.settings import settings
from xtv_support.core.bootstrap import build_context
from xtv_support.infrastructure.db.external_directory_config import save_config
from xtv_support.infrastructure.db.external_directory_secrets import store_secret_uri
from xtv_support.services.external_directory.accessors import get_user_signal_for
from xtv_support.services.external_directory.model import (
    DirectoryProviderLike,
    EnumRankMapping,
    ExternalDirectoryConfig,
    FieldKind,
    FieldMapping,
)
from xtv_support.services.rules.model import Condition, condition_matches


# Ensure we use mongomock.patch for the db
@pytest.fixture(autouse=True)
def patch_mongo():
    from unittest.mock import patch

    mock_client = AsyncMongoMockClient()
    with (
        patch("xtv_support.infrastructure.db.client.get_db") as mock_get_db,
        patch("xtv_support.core.bootstrap.get_db") as mock_boot_get_db,
        patch("xtv_support.infrastructure.db.migrations.run"),
    ):
        # also mock out ping_db
        async def mock_ping(*args, **kwargs):
            pass

        mock_get_db.return_value = mock_client.xtv_support_test
        mock_boot_get_db.return_value = mock_client.xtv_support_test

        # Mock db command to not fail
        with patch.object(
            mock_client.xtv_support_test, "command", new_callable=AsyncMock
        ) as mock_cmd:
            mock_cmd.return_value = {"ok": 1.0}
            yield mock_client


@pytest.fixture(autouse=True)
def setup_encryption_key():
    key = Fernet.generate_key()
    original_key = settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = SecretStr(key.decode("utf-8"))
    yield
    settings.EXTERNAL_DIRECTORY_ENCRYPTION_KEY = original_key


@pytest.mark.asyncio
async def test_external_directory_end_to_end(patch_mongo):
    # Setup mock core DB and external mock DB
    core_db = patch_mongo.xtv_support_test

    # 1. Setup our mock external collection
    ext_db = patch_mongo.test_external_db
    ext_col = ext_db.test_external_collection

    # Insert a generic doc matching our generic fictional schema
    await ext_col.insert_one(
        {
            "member_id": 555,
            "loyalty_level": "platinum",
            "valid_until": datetime.datetime.now(datetime.UTC).timestamp() + 3600,
        }
    )

    # 2. Save config in core_db mapping the external generic schema to internal XTV concepts
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="not_used_in_mongomock",
        database_name="test_external_db",
        collection_name="test_external_collection",
        external_id_field="member_id",
        external_id_is_string=False,
        field_mappings=(
            FieldMapping(
                local_name="tier_label",
                external_field_path="loyalty_level",
                kind=FieldKind.ENUM,
                enum_mapping=(
                    EnumRankMapping(
                        raw_value="platinum", rank_label="Platinum", rank_order=100, is_vip=True
                    ),
                    EnumRankMapping(
                        raw_value="gold", rank_label="Gold", rank_order=50, is_vip=False
                    ),
                ),
            ),
        ),
    )

    await save_config(core_db, config)

    # We mock out MotorClient in provider.py to use our mongomock client instead
    # Because provider will instantiate an AsyncIOMotorClient with the connection string.
    # To keep it simple, we patch MotorClient to return our mongomock client

    with pytest.MonkeyPatch.context() as m:

        def mock_motor_client(*args, **kwargs):
            return patch_mongo

        m.setattr(
            "xtv_support.services.external_directory.connection_manager.AsyncIOMotorClient",
            mock_motor_client,
        )

        await store_secret_uri(core_db, "mongodb://fake:27017")

        # 3. Build context to run the bootstrapping step (which evaluates logic in bootstrap.py)
        mock_client = AsyncMock()
        mock_client._ctx = None
        ctx = await build_context(mock_client)

        # 4. Fetch the provider and assert it is the real one, not the null one
        provider = ctx.container.resolve(DirectoryProviderLike)
        assert provider.__class__.__name__ == "ExternalDirectoryProvider"

        # 5. Fetch user signal via accessor using member_id = 555
        signal = await get_user_signal_for(ctx, 555)

        assert signal.is_vip is True
        assert signal.tier_label == "Platinum"
        assert signal.tier_rank_order == 100
        assert signal.source == "external_directory"

        # 6. Test Rules Engine condition_matches with user signal
        ticket = {"user_id": 555, "priority": "high"}

        cond_vip = Condition(field="user.is_vip", op="eq", value=True)
        cond_rank = Condition(field="user.tier_rank_order", op="gt", value=50)
        cond_bad = Condition(field="user.is_vip", op="eq", value=False)

        assert condition_matches(cond_vip, ticket, user_signal=signal) is True
        assert condition_matches(cond_rank, ticket, user_signal=signal) is True
        assert condition_matches(cond_bad, ticket, user_signal=signal) is False


@pytest.mark.asyncio
async def test_external_directory_fails_gracefully_on_bad_secret(patch_mongo):
    core_db = patch_mongo.xtv_support_test

    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="not_used",
        database_name="db",
        collection_name="col",
        external_id_field="member_id",
        external_id_is_string=False,
    )
    await save_config(core_db, config)

    # Intentionally do NOT store a secret so resolution fails

    mock_client = AsyncMock()
    mock_client._ctx = None
    ctx = await build_context(mock_client)

    # Should fallback to NullDirectoryProvider gracefully without crashing
    provider = ctx.container.resolve(DirectoryProviderLike)
    assert provider.__class__.__name__ == "NullDirectoryProvider"

    # Resolving a signal yields default
    signal = await get_user_signal_for(ctx, 555)
    assert signal.is_vip is False
    assert signal.source == "none"
