"""Built-in project templates auto-registered at import time."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.services.templates.builtins.billing import BILLING
from xtv_support.services.templates.builtins.community import COMMUNITY
from xtv_support.services.templates.builtins.contact import CONTACT
from xtv_support.services.templates.builtins.dev_github import DEV_GITHUB
from xtv_support.services.templates.builtins.feedback import FEEDBACK
from xtv_support.services.templates.builtins.support import SUPPORT
from xtv_support.services.templates.builtins.vip import VIP

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.services.templates.registry import TemplateRegistry


ALL = (SUPPORT, FEEDBACK, CONTACT, BILLING, DEV_GITHUB, VIP, COMMUNITY)


def register_all(registry: TemplateRegistry) -> None:
    registry.register_many(ALL)
