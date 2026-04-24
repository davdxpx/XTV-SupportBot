"""Simple anonymous contact form — zero routing, single inbox."""

from __future__ import annotations

from xtv_support.services.templates.model import MacroSeed, ProjectTemplate

CONTACT = ProjectTemplate(
    slug="contact",
    name="Contact Form",
    description="Single-inbox contact form. No team routing, no SLA timer.",
    icon="✉️",
    project_type="contact",
    welcome_card_title="Get in touch",
    welcome_card_body="Leave a message and we'll get back to you.",
    intake_fields=("message",),
    macros=(
        MacroSeed(
            name="ack",
            body="Message received, {user_name} — we'll get back to you soon.",
            tags=("ack",),
        ),
    ),
    default_priority="normal",
    default_tags=("contact",),
)
