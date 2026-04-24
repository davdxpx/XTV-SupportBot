"""Project templates — declarative seeds for new projects.

A :class:`~xtv_support.services.templates.model.ProjectTemplate` bundles
the settings, macros, KB articles, routing rules, SLA overrides and
welcome card a fresh project should start with. The runner installs a
template onto a new (or existing blank) project atomically where
possible.

Built-ins live under :mod:`xtv_support.services.templates.builtins`
and are auto-registered into :data:`default_registry` at import time.
Plugins can register their own via
``default_registry.register(ProjectTemplate(...))``.
"""

# Register built-ins on import so callers don't have to remember to.
from xtv_support.services.templates.builtins import register_all as _register_builtins
from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
    RoutingSeed,
    SlaOverrides,
)
from xtv_support.services.templates.registry import TemplateRegistry, default_registry
from xtv_support.services.templates.runner import InstallResult, install_template

_register_builtins(default_registry)

__all__ = [
    "InstallResult",
    "KbSeed",
    "MacroSeed",
    "ProjectTemplate",
    "RoutingSeed",
    "SlaOverrides",
    "TemplateRegistry",
    "default_registry",
    "install_template",
]
