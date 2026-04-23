"""AI sentiment tagger plugin.

Subscribes to :class:`MessageReceived` and enriches the ticket with a
sentiment label (positive / neutral / negative / urgent). Purely
additive — never modifies the user-facing reply flow.
"""
from xtv_support.plugins.builtin.ai_sentiment.plugin import Plugin

__all__ = ["Plugin"]
