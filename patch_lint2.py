with open("tests/integration/test_external_directory.py") as f:
    content = f.read()

content = content.replace(
    'patch("xtv_support.infrastructure.db.migrations.run") as mock_mig_run,',
    'patch("xtv_support.infrastructure.db.migrations.run"),',
)

with open("tests/integration/test_external_directory.py", "w") as f:
    f.write(content)
