"""VIP / white-glove template — 15m SLA, CSAT-required."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    MacroSeed,
    ProjectTemplate,
    RoutingSeed,
    SlaOverrides,
)

VIP = ProjectTemplate(
    slug="vip",
    name="VIP / White-glove Support",
    description=(
        "Highest-touch tier. 15-minute SLA, CSAT always on, personal greeting, auto-route "
        "to the VIP team."
    ),
    icon="💎",
    project_type="support",
    welcome_card_title="Welcome, VIP",
    welcome_card_body=(
        "You're in the VIP queue — our senior team will be with you in minutes. "
        "Anything we can help with today?"
    ),
    macros=(
        MacroSeed(
            name="vip_greet",
            body=(
                "Hello {user_name} — I'm personally looking after this for you. What's the context?"
            ),
            tags=("greeting", "vip"),
        ),
        MacroSeed(
            name="vip_confirm",
            body=(
                "Taken care of, {user_name}. I'll keep an eye on things for the next 24h — "
                "reach out any time."
            ),
            tags=("closing", "vip"),
        ),
    ),
    routing_rules=(RoutingSeed(weight=100, target_team_slug="vip"),),
    sla_overrides=SlaOverrides(warn_minutes=10, breach_minutes=15),
    csat_enabled=True,
    csat_required=True,
    default_priority="high",
    default_tags=("vip",),
    post_install_hint=(
        "Add your senior agents to the 'vip' team via /team before this project goes live."
    ),
)
