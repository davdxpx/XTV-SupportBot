with open("tests/integration/test_external_directory.py") as f:
    content = f.read()

content = content.replace(
    'patch("xtv_support.infrastructure.db.migrations.run") as mock_mig_run:',
    'patch("xtv_support.infrastructure.db.migrations.run"):  # noqa: F841',
)

with open("tests/integration/test_external_directory.py", "w") as f:
    f.write(content)

with open("tests/unit/services/rules/test_model.py") as f:
    content = f.read()

content = content.replace(
    "from xtv_support.services.external_directory.model import ResolvedUserSignal", ""
)
content = "from xtv_support.services.external_directory.model import ResolvedUserSignal\n" + content

with open("tests/unit/services/rules/test_model.py", "w") as f:
    f.write(content)
