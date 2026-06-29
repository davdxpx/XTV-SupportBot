with open("src/xtv_support/services/rules/dry_run.py") as f:
    content = f.read()

content = content.replace(
    "def dry_run(rule: Rule, ticket: dict) -> DryRunResult:",
    "def dry_run(rule: Rule, ticket: dict, *, user_signal: ResolvedUserSignal | None = None) -> DryRunResult:",
)

content = content.replace(
    "matched=condition_matches(c, ticket)",
    "matched=condition_matches(c, ticket, user_signal=user_signal)",
)

if "ResolvedUserSignal" not in content:
    content = content.replace(
        "from xtv_support.services.rules.model import Rule, condition_matches",
        "from xtv_support.services.external_directory.model import ResolvedUserSignal\nfrom xtv_support.services.rules.model import Rule, condition_matches",
    )

with open("src/xtv_support/services/rules/dry_run.py", "w") as f:
    f.write(content)
