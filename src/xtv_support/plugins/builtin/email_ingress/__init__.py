"""Email-ingestion plugin (scaffolding).

Full IMAP/SMTP integration lands in v0.10 — this stub exists so
``FEATURE_EMAIL_INGRESS`` exists in the flag matrix and the plugin
loader can discover/disable it consistently with the other bridges.
"""
from xtv_support.plugins.builtin.email_ingress.plugin import Plugin

__all__ = ["Plugin"]
