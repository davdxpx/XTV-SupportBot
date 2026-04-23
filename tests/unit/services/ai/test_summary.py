"""Ticket-summary tests — parser + end-to-end."""
from __future__ import annotations

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.summary import TicketSummary, parse, summarise


# ----------------------------------------------------------------------
# parse()
# ----------------------------------------------------------------------
def test_parse_happy_three_sections() -> None:
    text = (
        "Problem: User can't log in.\n"
        "Resolution: Agent reset the password.\n"
        "Tags: auth, login, password"
    )
    s = parse(text)
    assert s.ok
    assert s.problem == "User can't log in."
    assert s.resolution == "Agent reset the password."
    assert s.tags == ("auth", "login", "password")


def test_parse_multiline_section_bodies() -> None:
    text = (
        "Problem: Shipping\n"
        "was delayed three days.\n"
        "Resolution: Refund issued.\n"
        "Tags: shipping, refund"
    )
    s = parse(text)
    assert s.ok
    assert s.problem == "Shipping was delayed three days."
    assert s.resolution == "Refund issued."


def test_parse_tolerates_case_and_whitespace() -> None:
    text = "PROBLEM:X\n  RESOLUTION :   Y\ntags:a,b"
    s = parse(text)
    assert s.problem == "X"
    assert s.resolution == "Y"
    assert s.tags == ("a", "b")


def test_parse_missing_resolution_is_incomplete() -> None:
    text = "Problem: Something\nTags: x"
    s = parse(text)
    assert s.ok is False
    assert s.error == "incomplete"
    assert s.problem == "Something"
    assert s.resolution == ""


def test_parse_empty_input() -> None:
    s = parse("")
    assert not s.ok and s.error == "empty"


def test_parse_stores_raw_text() -> None:
    text = "Problem: x\nResolution: y\nTags: a"
    assert parse(text).raw == text


# ----------------------------------------------------------------------
# summarise()
# ----------------------------------------------------------------------
async def test_summarise_returns_parsed_payload() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Problem: Login failing.\n"
                            "Resolution: Reset password.\n"
                            "Tags: auth, login"
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 8},
        }

    client._call_litellm = fake
    s = await summarise(
        client,
        conversation_text="User: can't log in\nAgent: please reset",
        ticket_id="t1",
    )
    assert s.ok
    assert s.problem == "Login failing."
    assert s.tags == ("auth", "login")


async def test_summarise_disabled_returns_incomplete() -> None:
    client = AIClient(AIConfig(enabled=False))
    s = await summarise(client, conversation_text="...")
    assert s.ok is False
    assert s.error == "ai_disabled"
