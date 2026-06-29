with open("src/xtv_support/core/bootstrap.py") as f:
    content = f.read()

content = content.replace(
    "real_provider = ExternalDirectoryProvider(ext_dir_config, ExternalConnectionManager(), secret_uri)",
    "real_provider = ExternalDirectoryProvider(ext_dir_config, secret_uri, ExternalConnectionManager())",
)

with open("src/xtv_support/core/bootstrap.py", "w") as f:
    f.write(content)
