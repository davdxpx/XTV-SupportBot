with open("src/xtv_support/core/bootstrap.py") as f:
    content = f.read()

# Add connection manager import and initialization
if (
    "from xtv_support.services.external_directory.connection_manager import ExternalConnectionManager"
    not in content
):
    imports = """from xtv_support.services.external_directory.connection_manager import ExternalConnectionManager"""
    content = content.replace(
        "from xtv_support.services.external_directory.provider import ExternalDirectoryProvider",
        imports
        + "\nfrom xtv_support.services.external_directory.provider import ExternalDirectoryProvider",
    )

content = content.replace(
    "real_provider = ExternalDirectoryProvider(ext_dir_config, secret_uri)",
    "real_provider = ExternalDirectoryProvider(ext_dir_config, ExternalConnectionManager(secret_uri))",
)

with open("src/xtv_support/core/bootstrap.py", "w") as f:
    f.write(content)
