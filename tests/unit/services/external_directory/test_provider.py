import asyncio
import pytest

from xtv_support.services.external_directory.model import ExternalDirectoryConfig
from xtv_support.services.external_directory.provider import ExternalDirectoryProvider

# Mock AsyncIOMotorClient and DB
class MockCollection:
    def __init__(self, data, should_fail=False):
        self.data = data
        self.should_fail = should_fail

    async def find_one(self, query):
        if self.should_fail:
            from pymongo.errors import PyMongoError
            raise PyMongoError("DB Offline")
        key = list(query.keys())[0]
        val = query[key]
        return self.data.get(val)

class MockDB:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return self.collections.get(name, MockCollection({}))

class MockClient:
    def __init__(self, db_map):
        self.db_map = db_map

    def __getitem__(self, name):
        return self.db_map.get(name, MockDB({}))

@pytest.fixture
def base_config():
    return ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="mock_uri",
        database_name="test_db",
        collection_name="test_coll",
        external_id_field="user_id",
    )

@pytest.mark.asyncio
async def test_provider_success(base_config):
    data = {123: {"user_id": 123, "is_vip": True}}

    mock_coll = MockCollection(data)
    mock_db = MockDB({"test_coll": mock_coll})
    mock_client = MockClient({"test_db": mock_db})

    provider = ExternalDirectoryProvider(
        base_config,
        client_factory=lambda _: mock_client
    )

    sig = await provider.get_signal(123)
    assert not sig.is_vip # No mapping applied, so default False
    assert sig.source == "external_directory"

    sig_not_found = await provider.get_signal(456)
    assert sig_not_found.source == "none"

@pytest.mark.asyncio
async def test_provider_failure_graceful(base_config):
    mock_coll = MockCollection({}, should_fail=True)
    mock_db = MockDB({"test_coll": mock_coll})
    mock_client = MockClient({"test_db": mock_db})

    provider = ExternalDirectoryProvider(
        base_config,
        client_factory=lambda _: mock_client
    )

    sig = await provider.get_signal(123)
    assert not sig.is_vip
    assert sig.source == "none"

@pytest.mark.asyncio
async def test_provider_caching(base_config):
    data = {123: {"user_id": 123}}
    mock_coll = MockCollection(data)
    mock_db = MockDB({"test_coll": mock_coll})
    mock_client = MockClient({"test_db": mock_db})

    provider = ExternalDirectoryProvider(
        base_config,
        client_factory=lambda _: mock_client
    )

    # First call caches it
    await provider.get_signal(123)
    assert 123 in provider._cache

    # Second call hits cache (even if we change data underneath, mock_coll is not called)
    mock_coll.data = {123: None}
    sig = await provider.get_signal(123)
    assert sig.source == "external_directory"

    # Clear cache
    provider.clear_cache()
    assert len(provider._cache) == 0

    # Invalidate specific
    await provider.get_signal(123)
    provider.invalidate(123)
    assert len(provider._cache) == 0
