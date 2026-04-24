"""Community template — pre-seeded for public Telegram group mirroring."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
)

COMMUNITY = ProjectTemplate(
    slug="community",
    name="Community & Discussion",
    description=(
        "Low-noise support for a public Telegram community. KB gate on, SLA off, auto-close 7 days."
    ),
    icon="👥",
    project_type="support",
    welcome_card_title="Community help",
    welcome_card_body=(
        "Drop your question here — the community and a moderator will chip in. "
        "For account-specific issues, use the main support queue."
    ),
    macros=(
        MacroSeed(
            name="ack_community",
            body=(
                "Thanks for posting, {user_name}! A moderator will swing by and others in "
                "the community might jump in too."
            ),
            tags=("ack",),
        ),
        MacroSeed(
            name="redirect_to_support",
            body=(
                "This looks like an account-specific issue, {user_name}. Could you open "
                "a ticket via the main support queue so we can check your account privately?"
            ),
            tags=("redirect",),
        ),
    ),
    kb_articles=(
        KbSeed(
            slug="community_rules",
            title="Community rules",
            body=(
                "Be kind. No spam. No solicitation. No piracy. Moderators reserve the right "
                "to remove anything off-topic."
            ),
            tags=("rules", "community"),
        ),
    ),
    default_priority="low",
    default_tags=("community",),
    feature_flag_overrides=(("FEATURE_KB_GATE", True),),
)
