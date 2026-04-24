"""Knowledge-base events."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class KbArticleShown(DomainEvent):
    """The gate presented an article to a user (pre-ticket)."""

    article_id: str
    slug: str
    user_id: int
    query: str | None = None
    rank: int = 0  # position in the suggestion list (0 = first)


@dataclass(frozen=True, slots=True, kw_only=True)
class KbArticleHelpful(DomainEvent):
    """User clicked "this helped" on the presented article."""

    article_id: str
    slug: str
    user_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class KbArticleDismissed(DomainEvent):
    """User chose "talk to a human" or dismissed the gate."""

    article_id: str | None = None
    user_id: int
    query: str | None = None
    reason: str = "humanplease"  # humanplease | timeout | explicit
