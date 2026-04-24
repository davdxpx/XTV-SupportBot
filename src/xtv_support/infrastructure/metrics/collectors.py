"""Named metric handles for the rest of the codebase.

Services import these via::

    from xtv_support.infrastructure.metrics.collectors import MESSAGES_IN

    MESSAGES_IN.labels(direction="in", type="text").inc()

All handles are backed by :mod:`registry` so they degrade to a no-op
when ``prometheus_client`` is not installed.
"""

from __future__ import annotations

from xtv_support.infrastructure.metrics.registry import counter, histogram

MESSAGES_IN = counter(
    "xtv_messages_total",
    "Number of Telegram updates received, by direction + content type.",
    labels=["direction", "type"],
)

TICKETS_TOTAL = counter(
    "xtv_tickets_total",
    "Ticket lifecycle events, split by state and project.",
    labels=["state", "project"],
)

SLA_BREACHES = counter(
    "xtv_sla_breaches_total",
    "Count of SLA breaches.",
    labels=["team"],
)

AI_TOKENS = counter(
    "xtv_ai_tokens_total",
    "AI tokens consumed by feature + model.",
    labels=["model", "feature"],
)

AI_COST_USD = counter(
    "xtv_ai_cost_usd_total",
    "Cumulative AI spend in USD.",
    labels=["model"],
)

WEBHOOK_DELIVERIES = counter(
    "xtv_webhook_deliveries_total",
    "Outgoing webhook deliveries.",
    labels=["status"],
)

BROADCAST_MESSAGES = counter(
    "xtv_broadcast_messages_total",
    "Broadcast message deliveries.",
    labels=["status"],
)

HANDLER_DURATION = histogram(
    "xtv_handler_duration_seconds",
    "End-to-end handler execution time.",
    labels=["handler"],
)

DB_QUERY_DURATION = histogram(
    "xtv_db_query_duration_seconds",
    "DB query time by collection.",
    labels=["collection"],
)
