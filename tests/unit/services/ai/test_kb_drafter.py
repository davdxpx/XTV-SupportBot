"""KB-drafter parser + service tests."""
from __future__ import annotations

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.kb_drafter import KbDraft, draft_article, parse


# ----------------------------------------------------------------------
# parse()
# ----------------------------------------------------------------------
def test_parse_happy_three_sections() -> None:
    text = (
        "Title: Reset your password\n"
        "Tags: auth, password, login\n"
        "Body:\n"
        "Open the account settings.\n"
        "Click 'Reset password'."
    )
    d = parse(text)
    assert d.ok
    assert d.title == "Reset your password"
    assert d.tags == ("auth", "password", "login")
    assert d.body == "Open the account settings.\nClick 'Reset password'."


def test_parse_body_can_be_multiline_without_leading_line() -> None:
    text = "Title: T\nTags: a\nBody: first line\nsecond line"
    d = parse(text)
    assert d.ok
    assert d.body == "first line\nsecond line"


def test_parse_missing_body_is_incomplete() -> None:
    text = "Title: X\nTags: t1"
    d = parse(text)
    assert not d.ok
    assert d.error == "incomplete"


def test_parse_missing_title_is_incomplete() -> None:
    text = "Tags: t1\nBody: x"
    d = parse(text)
    assert not d.ok


def test_parse_empty_input() -> None:
    d = parse("")
    assert not d.ok
    assert d.error == "empty"


def test_parse_preserves_raw() -> None:
    text = "Title: T\nTags:\nBody: x"
    d = parse(text)
    assert d.raw == text


# ----------------------------------------------------------------------
# draft_article()
# ----------------------------------------------------------------------
async def test_draft_article_returns_structured_draft() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Title: Fix the thing\n"
                            "Tags: fix, howto\n"
                            "Body:\nClick the button.\nThen click again."
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 20},
        }

    client._call_litellm = fake
    d = await draft_article(
        client,
        conversation_text="user: broken / agent: fixed",
        ticket_id="t1",
    )
    assert d.ok
    assert d.title == "Fix the thing"
    assert d.tags == ("fix", "howto")
    assert "Click the button." in d.body


async def test_draft_article_disabled() -> None:
    client = AIClient(AIConfig(enabled=False))
    d = await draft_article(client, conversation_text="...")
    assert not d.ok
    assert d.error == "ai_disabled"
