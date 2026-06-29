with open("tests/integration/test_external_directory.py") as f:
    content = f.read()

# remove patch for AsyncIOMotorDatabase as it is imported inside try-except inside bootstrap.py
content = content.replace(
    """        with patch("xtv_support.core.bootstrap.AsyncIOMotorDatabase", autospec=True):
            # Patch the retry ping db loop
            with patch("xtv_support.core.bootstrap.async_retry", lambda **kwargs: lambda f: mock_ping):
                yield mock_client""",
    """        # Patch the ping_db directly to avoid Event loop is closed
        with patch("xtv_support.core.bootstrap._ping_db", new_callable=AsyncMock) as mock_ping:
            yield mock_client""",
)

with open("tests/integration/test_external_directory.py", "w") as f:
    f.write(content)
