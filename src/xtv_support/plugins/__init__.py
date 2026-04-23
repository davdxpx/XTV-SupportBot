"""Plugin system — base class, registry, loader, built-ins.

Plugins can register handlers, commands, event subscribers and migrations.
The loader discovers built-ins in `xtv_support.plugins.builtin` and
third-party packages via the `xtv_support.plugins` entry-point group.

Introduced in Phase 3.
"""
