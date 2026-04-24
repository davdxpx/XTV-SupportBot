"""Knowledge-base article domain model.

An article is the smallest standalone answer that can resolve a user
question without opening a ticket. The KB gate (Phase 6c) offers
matching articles as inline buttons before a new ticket is created.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class KbArticle:
    """Immutable representation of one KB article."""

    id: str
    slug: str  # URL-safe unique id
    title: str
    body: str  # HTML-safe content
    lang: str = "en"  # locale code — ties into i18n
    tags: tuple[str, ...] = ()
    project_ids: tuple[str, ...] = ()  # scope: which projects see this article
    views: int = 0
    helpful: int = 0
    not_helpful: int = 0
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def helpfulness(self) -> float:
        """Helpful ratio 0..1. Returns 0 when the article has no feedback."""
        total = self.helpful + self.not_helpful
        return 0.0 if total == 0 else round(self.helpful / total, 3)
