"""Billing / payments — strict SLA, VIP hooks, refund playbook."""

from __future__ import annotations

from xtv_support.services.templates.model import (
    KbSeed,
    MacroSeed,
    ProjectTemplate,
    RoutingSeed,
    SlaOverrides,
)

BILLING = ProjectTemplate(
    slug="billing",
    name="Billing & Payments",
    description=(
        "Payments, invoices, refunds, subscription issues. Strict SLA (30m warn / "
        "60m breach) and VIP tag auto-applied."
    ),
    icon="💳",
    project_type="support",
    welcome_card_title="Billing support",
    welcome_card_body=(
        "Tell us the issue and — if comfortable — the last 4 digits of the card or "
        "the invoice number. <b>Never share full card numbers.</b>"
    ),
    intake_fields=("what_happened", "invoice_number", "payment_method"),
    macros=(
        MacroSeed(
            name="refund_ack",
            body=(
                "Understood, {user_name}. I'll process the refund and the amount typically "
                "appears back on your card in 3–5 business days. I'll confirm once it's queued."
            ),
            tags=("refund", "ack"),
        ),
        MacroSeed(
            name="refund_done",
            body=(
                "Refund processed, {user_name}. Reference: see your email receipt. "
                "Anything else I can help with?"
            ),
            tags=("refund", "closing"),
        ),
        MacroSeed(
            name="verify_identity",
            body=(
                "Before I can make changes to the billing account, I'll need to verify "
                "ownership — could you share the email on file and the last 4 digits of the "
                "payment method? Thanks, {user_name}."
            ),
            tags=("security",),
        ),
    ),
    kb_articles=(
        KbSeed(
            slug="when_refunds_arrive",
            title="When will my refund arrive?",
            body="Refunds typically settle in 3–5 business days, depending on your bank.",
            tags=("refund", "faq"),
        ),
        KbSeed(
            slug="update_payment_method",
            title="How do I update my payment method?",
            body="Log into your account → Billing → Payment methods → Edit.",
            tags=("payments", "faq"),
        ),
    ),
    routing_rules=(
        RoutingSeed(match_tag="billing", weight=20, target_team_slug="billing"),
        RoutingSeed(match_tag="refund", weight=20, target_team_slug="billing"),
        RoutingSeed(match_priority="high", weight=10, target_team_slug="billing"),
    ),
    sla_overrides=SlaOverrides(warn_minutes=30, breach_minutes=60),
    csat_enabled=True,
    default_priority="high",
    default_tags=("billing",),
    post_install_hint=(
        "Heads up: SLA is stricter than the global default. Make sure your billing team "
        "timezone + business hours are set."
    ),
)
