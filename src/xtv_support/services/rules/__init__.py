"""Automation rules engine — event-driven if/then pipelines."""

from xtv_support.services.rules.evaluator import RuleEvaluator
from xtv_support.services.rules.model import ActionRef, Condition, Rule
from xtv_support.services.rules.repository import (
    create_rule,
    delete_rule,
    enable_rule,
    get_rule,
    list_rules,
)

__all__ = [
    "ActionRef",
    "Condition",
    "Rule",
    "RuleEvaluator",
    "create_rule",
    "delete_rule",
    "enable_rule",
    "get_rule",
    "list_rules",
]
