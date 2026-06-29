with open("src/xtv_support/core/bootstrap.py") as f:
    content = f.read()

# Add necessary imports
imports = """
from xtv_support.services.external_directory.null_provider import NullDirectoryProvider
from xtv_support.services.external_directory.provider import ExternalDirectoryProvider
from xtv_support.services.external_directory.model import DirectoryProviderLike
from xtv_support.infrastructure.db.external_directory_config import get_config as get_external_dir_config
from xtv_support.infrastructure.db.external_directory_secrets import resolve_secret_uri
"""

content = content.replace(
    "from xtv_support.services.rules.evaluator import RuleEvaluator",
    imports + "\nfrom xtv_support.services.rules.evaluator import RuleEvaluator",
)

# Update RuleEvaluator initialization
content = content.replace(
    "rules = RuleEvaluator(db=db, bus=bus, actions=actions, client=client)",
    "rules = RuleEvaluator(db=db, bus=bus, actions=actions, container=container, client=client)",
)

# After Phase 3 kernel logic, register NullDirectoryProvider and then attempt to fetch external directory config
registration_code = """
    # --- External User Directory Setup ---
    container.register_instance(DirectoryProviderLike, NullDirectoryProvider())

    ext_dir_config = await get_external_dir_config(db)
    if ext_dir_config and ext_dir_config.enabled:
        try:
            secret_uri = await resolve_secret_uri(db)
            if secret_uri:
                real_provider = ExternalDirectoryProvider(ext_dir_config, secret_uri)
                container.register_instance(DirectoryProviderLike, real_provider, override=True)
                log.info("external_directory.provider_bound", database=ext_dir_config.database_name)
        except Exception as e:
            log.error("external_directory.provider_failed", error=str(e), context="secret resolution failed")
            # NullDirectoryProvider remains bound

    # --- Classic services (unchanged) -------------------------------"""

content = content.replace(
    "    # --- Classic services (unchanged) -------------------------------", registration_code
)

with open("src/xtv_support/core/bootstrap.py", "w") as f:
    f.write(content)
