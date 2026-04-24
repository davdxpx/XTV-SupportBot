"""Developer / GitHub bug-report intake."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
    RoutingSeed,
)

DEV_GITHUB = ProjectTemplate(
    slug="dev_github",
    name="Developer Bug Reports",
    description=(
        "Structured bug intake (repro / expected / actual / env). GitHub webhook "
        "out-of-the-box when FEATURE_WEBHOOKS_OUT=true."
    ),
    icon="🐛",
    project_type="support",
    welcome_card_title="Report a bug",
    welcome_card_body=(
        "Help us fix it fast: share what you tried, what you expected, what actually "
        "happened, and a minimal repro."
    ),
    intake_fields=(
        "repro_steps",
        "expected_behaviour",
        "actual_behaviour",
        "environment",
        "version",
    ),
    macros=(
        MacroSeed(
            name="need_repro",
            body=(
                "Thanks, {user_name}. To reproduce this I'll need:\n"
                "• Exact steps (1, 2, 3…)\n"
                "• Expected behaviour\n"
                "• Actual behaviour\n"
                "• Environment (OS, browser, app version)"
            ),
            tags=("info_request",),
        ),
        MacroSeed(
            name="opened_issue",
            body=(
                "Tracked this on GitHub — I'll keep you posted when there's movement. "
                "Thanks for the clean report, {user_name}."
            ),
            tags=("closing",),
        ),
    ),
    kb_articles=(
        KbSeed(
            slug="good_bug_reports",
            title="Anatomy of a great bug report",
            body=(
                "Include: steps, expected, actual, environment, version, screenshots or "
                "logs. The tighter the repro, the faster the fix."
            ),
            tags=("bug-report", "faq"),
        ),
    ),
    routing_rules=(
        RoutingSeed(match_tag="bug", weight=15, target_team_slug="dev"),
        RoutingSeed(match_project_type="support", weight=1, target_team_slug="dev"),
    ),
    default_priority="normal",
    default_tags=("bug", "dev"),
    post_install_hint=(
        "Set WEBHOOK_SECRET + FEATURE_WEBHOOKS_OUT=true to wire this to GitHub issues."
    ),
)
