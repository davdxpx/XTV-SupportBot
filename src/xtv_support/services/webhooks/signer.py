"""HMAC-SHA-256 signature helpers for outgoing webhooks.

Receivers verify ``X-XTV-Signature`` against the request body using
the shared secret they configured when registering the webhook. The
signature is a lowercase hex digest prefixed with ``sha256=`` so
consumers familiar with GitHub's webhook scheme feel at home.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass


SIGNATURE_HEADER = "X-XTV-Signature"
EVENT_HEADER = "X-XTV-Event"
DELIVERY_HEADER = "X-XTV-Delivery"
TIMESTAMP_HEADER = "X-XTV-Timestamp"


@dataclass(frozen=True, slots=True)
class SignedPayload:
    body: bytes
    headers: dict[str, str]


def sign(
    *,
    body: bytes,
    secret: str,
    event: str,
    timestamp: int,
    delivery_id: str | None = None,
) -> SignedPayload:
    """Build the headers a receiver needs to verify + dispatch an event."""
    if not secret:
        raise ValueError("webhook secret is required")
    delivery = delivery_id or str(uuid.uuid4())
    digest = hmac.new(
        secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return SignedPayload(
        body=body,
        headers={
            SIGNATURE_HEADER: f"sha256={digest}",
            EVENT_HEADER: event,
            DELIVERY_HEADER: delivery,
            TIMESTAMP_HEADER: str(timestamp),
            "Content-Type": "application/json",
        },
    )


def verify(*, body: bytes, secret: str, signature: str) -> bool:
    """Timing-safe verify. ``signature`` may include the ``sha256=`` prefix."""
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    candidate = signature[len("sha256=") :] if signature.startswith("sha256=") else signature
    return secrets.compare_digest(expected, candidate)
