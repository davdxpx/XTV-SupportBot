"""Prompt-builder unit tests."""
from __future__ import annotations

from xtv_support.services.ai import prompts


def test_draft_prompt_shape() -> None:
    msgs = prompts.build_draft_prompt(
        conversation=[
            {"role": "user", "content": "My login doesn't work"},
            {"role": "assistant", "content": "Have you tried a reset?"},
        ],
        pending_user_message="Yes, twice.",
    )
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == prompts.SYSTEM_DRAFT_REPLY
    assert msgs[1]["role"] == "user"
    assert msgs[-1]["content"] == "Yes, twice."
    assert len(msgs) == 4


def test_summary_prompt_shape() -> None:
    msgs = prompts.build_summary_prompt("conversation log here")
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == prompts.SYSTEM_SUMMARY
    assert msgs[1]["content"] == "conversation log here"


def test_sentiment_prompt_shape() -> None:
    msgs = prompts.build_sentiment_prompt("everything is broken!!!")
    assert msgs[0]["role"] == "system"
    assert "positive" in msgs[0]["content"] and "urgent" in msgs[0]["content"]
    assert msgs[1]["content"] == "everything is broken!!!"


def test_routing_prompt_formats_team_block() -> None:
    msgs = prompts.build_routing_prompt(
        user_text="billing issue",
        teams=[("billing", "Billing + invoices"), ("support", "General")],
    )
    assert msgs[0]["role"] == "system"
    content = msgs[1]["content"]
    assert "billing: Billing + invoices" in content
    assert "support: General" in content
    assert "billing issue" in content


def test_translate_prompt_substitutes_target_lang() -> None:
    msgs = prompts.build_translate_prompt(
        source_text="Hallo Welt", target_lang="English"
    )
    assert "into English" in msgs[0]["content"]
    assert msgs[1]["content"] == "Hallo Welt"


def test_kb_drafter_prompt_shape() -> None:
    msgs = prompts.build_kb_drafter_prompt("conversation")
    assert msgs[0]["role"] == "system"
    assert "Title:" in msgs[0]["content"]
    assert msgs[1]["content"] == "conversation"


def test_system_prompts_are_non_empty() -> None:
    for attr in dir(prompts):
        if attr.startswith("SYSTEM_"):
            value = getattr(prompts, attr)
            assert isinstance(value, str) and value.strip(), attr
