with open("tests/integration/test_external_directory.py") as f:
    content = f.read()

# Replace mongomock patch logic to use mongomock_motor so `await` works properly
content = content.replace(
    """import mongomock.mongo_client""", """from mongomock_motor import AsyncMongoMockClient"""
)

content = content.replace(
    """# Ensure we use mongomock.patch for the db
@pytest.fixture(autouse=True)
def patch_mongo():
    from unittest.mock import patch

    mock_client = mongomock.mongo_client.MongoClient()
    with patch("xtv_support.infrastructure.db.client.get_db") as mock_get_db:
        mock_get_db.return_value = mock_client.xtv_support_test
        yield mock_client""",
    """# Ensure we use mongomock.patch for the db
@pytest.fixture(autouse=True)
def patch_mongo():
    from unittest.mock import patch

    mock_client = AsyncMongoMockClient()
    with patch("xtv_support.infrastructure.db.client.get_db") as mock_get_db:
        mock_get_db.return_value = mock_client.xtv_support_test
        yield mock_client""",
)

content = content.replace(
    """    # Insert a generic doc matching our generic fictional schema
    ext_col.insert_one({""",
    """    # Insert a generic doc matching our generic fictional schema
    await ext_col.insert_one({""",
)

with open("tests/integration/test_external_directory.py", "w") as f:
    f.write(content)
