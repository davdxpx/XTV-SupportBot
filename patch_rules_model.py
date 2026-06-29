with open("src/xtv_support/services/rules/model.py") as f:
    content = f.read()

content = content.replace(
    "def condition_matches(cond: Condition, ticket: dict) -> bool:",
    """def _user_signal_to_dict(signal: ResolvedUserSignal) -> dict:
    return {
        "is_vip": signal.is_vip,
        "tier_label": signal.tier_label,
        "tier_rank_order": signal.tier_rank_order,
        "priority_score": signal.priority_score,
        "display_badge": signal.display_badge,
        "source": signal.source,
    }


def condition_matches(
    cond: Condition, ticket: dict, *, user_signal: ResolvedUserSignal | None = None
) -> bool:""",
)

content = content.replace(
    "value = _walk(ticket, cond.field)",
    """if cond.field.startswith("user."):
        if user_signal is None:
            return False
        value = _walk(_user_signal_to_dict(user_signal), cond.field[5:])
    else:
        value = _walk(ticket, cond.field)""",
)

content = content.replace(
    "def all_conditions_match(conds: tuple[Condition, ...], ticket: dict) -> bool:\n    return all(condition_matches(c, ticket) for c in conds)",
    """def all_conditions_match(
    conds: tuple[Condition, ...], ticket: dict, *, user_signal: ResolvedUserSignal | None = None
) -> bool:
    return all(condition_matches(c, ticket, user_signal=user_signal) for c in conds)""",
)

# Also need to import ResolvedUserSignal if not already imported
if "ResolvedUserSignal" not in content:
    content = content.replace(
        "from dataclasses import dataclass, field",
        "from dataclasses import dataclass, field\n\nfrom xtv_support.services.external_directory.model import ResolvedUserSignal",
    )

with open("src/xtv_support/services/rules/model.py", "w") as f:
    f.write(content)
