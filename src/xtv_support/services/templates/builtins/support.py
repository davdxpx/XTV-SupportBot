"""Generic tech-support template — the safe default."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
    RoutingSeed,
)

SUPPORT = ProjectTemplate(
    slug="support",
    name="Technical Support",
    description="Generic support queue — tickets, macros, KB articles, standard SLA.",
    icon="🛠️",
    project_type="support",
    welcome_card_title="How can we help?",
    welcome_card_body=(
        "Tell us what's going on and we'll get back to you as soon as possible. "
        "Include any error message, what you expected, and what actually happened."
    ),
    intake_fields=("what_happened", "expected_behaviour", "steps_to_reproduce"),
    macros=(
        MacroSeed(
            name="greet",
            body="Hi {user_name}! Thanks for reaching out — I'll take a look right away.",
            tags=("greeting",),
        ),
        MacroSeed(
            name="ack",
            body="Got it, {user_name}. I'm looking into this now and will get back to you shortly.",
            tags=("ack",),
        ),
        MacroSeed(
            name="more_info",
            body=(
                "To help me reproduce this, could you share:\n"
                "• The exact error message\n"
                "• What you were doing when it happened\n"
                "• Screenshots if possible"
            ),
            tags=("info_request",),
        ),
        MacroSeed(
            name="resolved",
            body="Glad that worked out, {user_name}! Closing this out — feel free to open a new ticket any time.",
            tags=("closing",),
        ),
    ),
    kb_articles=(
        KbSeed(
            slug="how_to_report_bug",
            title="How to report a bug",
            body="Include the error message, what you expected, and steps to reproduce. "
            "Screenshots speed things up a lot.",
            tags=("bug-report", "faq"),
        ),
        KbSeed(
            slug="response_times",
            title="What are your response times?",
            body="We reply within 30 minutes during business hours. After hours, expect a "
            "response the next working day.",
            tags=("sla", "faq"),
        ),
        KbSeed(
            slug="contact_hours",
            title="When are you available?",
            body="Monday–Friday, 09:00–18:00 CET. Urgent issues outside these hours are still "
            "answered when an on-call agent is available.",
            tags=("hours", "faq"),
        ),
    ),
    routing_rules=(
        RoutingSeed(match_priority="high", weight=10, target_team_slug="support"),
        RoutingSeed(weight=1, target_team_slug="support"),
    ),
    sla_overrides=None,  # uses the global defaults
    default_priority="normal",
    default_tags=("support",),
    post_install_hint=("Tip: run /macro list to see the pre-seeded macros you can use in topics."),
)
