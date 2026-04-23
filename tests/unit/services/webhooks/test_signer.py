"""HMAC signer + verifier tests."""
from __future__ import annotations

import json

import pytest

from xtv_support.services.webhooks.signer import (
    DELIVERY_HEADER,
    EVENT_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign,
    verify,
)


def test_sign_populates_all_headers() -> None:
    body = json.dumps({"hello": "world"}).encode()
    signed = sign(
        body=body, secret="s3cret", event="ticket.created", timestamp=1_700_000_000
    )
    assert signed.headers[EVENT_HEADER] == "ticket.created"
    assert signed.headers[TIMESTAMP_HEADER] == "1700000000"
    assert signed.headers[SIGNATURE_HEADER].startswith("sha256=")
    assert signed.headers["Content-Type"] == "application/json"
    # delivery id is a UUID4-shaped string
    assert len(signed.headers[DELIVERY_HEADER]) == 36


def test_sign_round_trips_via_verify() -> None:
    body = b"payload"
    signed = sign(body=body, secret="k", event="e", timestamp=0)
    assert verify(body=body, secret="k", signature=signed.headers[SIGNATURE_HEADER])


def test_verify_rejects_wrong_secret() -> None:
    body = b"payload"
    signed = sign(body=body, secret="right", event="e", timestamp=0)
    assert not verify(body=body, secret="wrong", signature=signed.headers[SIGNATURE_HEADER])


def test_verify_rejects_modified_body() -> None:
    signed = sign(body=b"original", secret="k", event="e", timestamp=0)
    assert not verify(body=b"tampered", secret="k", signature=signed.headers[SIGNATURE_HEADER])


def test_verify_accepts_signature_without_prefix() -> None:
    signed = sign(body=b"x", secret="k", event="e", timestamp=0)
    sig = signed.headers[SIGNATURE_HEADER]
    assert sig.startswith("sha256=")
    assert verify(body=b"x", secret="k", signature=sig[len("sha256="):])


def test_verify_empty_inputs() -> None:
    assert not verify(body=b"x", secret="", signature="sha256=abc")
    assert not verify(body=b"x", secret="k", signature="")


def test_sign_rejects_empty_secret() -> None:
    with pytest.raises(ValueError):
        sign(body=b"x", secret="", event="e", timestamp=0)


def test_delivery_id_override() -> None:
    signed = sign(
        body=b"x", secret="k", event="e", timestamp=0, delivery_id="my-delivery-1"
    )
    assert signed.headers[DELIVERY_HEADER] == "my-delivery-1"
