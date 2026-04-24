"""Feedback / feature-request collector template."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
)

FEEDBACK = ProjectTemplate(
    slug="feedback",
    name="Feedback & Feature Requests",
    description=(
        "Low-noise inbox for feature requests + product feedback. No SLA, auto-close "
        "after 30 days of silence."
    ),
    icon="💡",
    project_type="feedback",
    welcome_card_title="Share your feedback",
    welcome_card_body=(
        "Tell us what's missing, what's great, or what you'd love to see. Every idea "
        "gets read — we can't always reply individually but nothing goes to the void."
    ),
    intake_fields=("suggestion", "why_it_matters"),
    macros=(
        MacroSeed(
            name="thanks",
            body="Thanks for the idea, {user_name}! I've logged it for the team to review.",
            tags=("ack",),
        ),
        MacroSeed(
            name="shipped",
            body=(
                "Great news, {user_name} — this suggestion shipped! Details: "
                "https://github.com/davdxpx/XTV-SupportBot/releases"
            ),
            tags=("closing",),
        ),
    ),
    kb_articles=(
        KbSeed(
            slug="where_do_ideas_go",
            title="Where do submitted ideas go?",
            body=(
                "Every submission is triaged weekly. High-impact items land in the public "
                "roadmap; others may be batched into a 'next quarter' review."
            ),
            tags=("faq",),
        ),
    ),
    sla_overrides=None,
    default_priority="low",
    default_tags=("feedback",),
)
