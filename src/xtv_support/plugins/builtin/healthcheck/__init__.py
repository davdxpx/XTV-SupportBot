"""Healthcheck plugin — smoke-proof that the loader works.

Subscribes to :class:`PluginLoaded` and simply counts how many plugins
came up. Intentionally minimal, no feature flag; it always loads.
"""
from xtv_support.plugins.builtin.healthcheck.plugin import Plugin

__all__ = ["Plugin"]
