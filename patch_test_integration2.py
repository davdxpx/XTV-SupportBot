with open("tests/integration/test_external_directory.py") as f:
    content = f.read()

# remove patch for AsyncIOMotorDatabase as it is imported inside try-except inside bootstrap.py
# `_ping_db` is local to `build_context`, it is not a module attribute.
# So we need to mock db.command to not fail
content = content.replace(
    """        # Patch the ping_db directly to avoid Event loop is closed
        with patch("xtv_support.core.bootstrap._ping_db", new_callable=AsyncMock) as mock_ping:
            yield mock_client""",
    """        # Mock db command to not fail
        with patch.object(mock_client.xtv_support_test, 'command', new_callable=AsyncMock) as mock_cmd:
            mock_cmd.return_value = {"ok": 1.0}
            yield mock_client""",
)

with open("tests/integration/test_external_directory.py", "w") as f:
    f.write(content)
