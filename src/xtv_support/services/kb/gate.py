"""Pre-ticket KB gate.

When a user sends a free-text question, this gate decides whether to
short-circuit into the knowledge base (offer suggestions + let them
dismiss with ``/humanplease``) or fall through to the normal ticket
flow. The gate is a **pure function** — the pyrofork handler in
``handlers/user/kb_gate.py`` is a thin wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import KbArticleShown
from xtv_support.domain.models.kb import KbArticle
from xtv_support.services.kb.service import search

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.core.events import EventBus

_log = get_logger("kb.gate")


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of a single gate evaluation."""

    #: Up to 3 articles the handler should present. Empty -> gate didn't trigger.
    suggestions: tuple[KbArticle, ...] = ()

    @property
    def triggered(self) -> bool:
        return bool(self.suggestions)


async def evaluate(
    db: AsyncIOMotorDatabase,
    bus: EventBus | None,
    *,
    user_id: int,
    query: str,
    lang: str | None = None,
    default_lang: str = "en",
    project_id: str | None = None,
    max_suggestions: int = 3,
) -> GateResult:
    """Return the top-N KB articles for ``query`` and announce the show.

    When the gate triggers (at least one hit), a :class:`KbArticleShown`
    event is published for *each* suggestion with its 0-based rank. The
    handler presents them as inline buttons; later phases aggregate
    those events for relevance analytics.

    When ``bus`` is ``None`` the events are skipped (useful in tests).
    """
    results = await search(
        db,
        query,
        lang=lang,
        default_lang=default_lang,
        project_id=project_id,
        limit=max_suggestions,
    )
    if not results:
        return GateResult()

    if bus is not None:
        for rank, article in enumerate(results):
            await bus.publish(
                KbArticleShown(
                    article_id=article.id,
                    slug=article.slug,
                    user_id=user_id,
                    query=query,
                    rank=rank,
                )
            )

    _log.info(
        "kb.gate.triggered",
        user_id=user_id,
        query=query[:60],
        hits=len(results),
    )
    return GateResult(suggestions=tuple(results))
