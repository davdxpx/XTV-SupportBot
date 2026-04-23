"""Knowledge-base service.

Composition layer over the repo that:

* Normalises the search query (strips, lower-cases, drops tiny tokens).
* Prefers the user's locale but falls back to ``default_lang`` when
  the locale has no matching articles.
* Filters by project when the user just selected one.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.models.kb import KbArticle
from xtv_support.infrastructure.db import kb as kb_repo

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("kb")

MIN_QUERY_LEN = 3


def normalise_query(raw: str) -> str:
    """Trim, collapse whitespace, lowercase."""
    if not raw:
        return ""
    return " ".join(raw.lower().split())


async def search(
    db: "AsyncIOMotorDatabase",
    raw_query: str,
    *,
    lang: str | None = None,
    default_lang: str = "en",
    project_id: str | None = None,
    limit: int = 3,
) -> list[KbArticle]:
    """High-level search used by the pre-ticket gate."""
    query = normalise_query(raw_query)
    if len(query) < MIN_QUERY_LEN:
        return []

    # First try the user's locale (if given) — then fall back to the
    # default locale. Most KB content lives in ``en`` so this ensures
    # non-English users still get answers.
    for candidate in _locale_fallback(lang, default_lang):
        results = await kb_repo.search(
            db, query, lang=candidate, project_id=project_id, limit=limit
        )
        if results:
            _log.debug(
                "kb.search.hit",
                query=query,
                lang=candidate,
                hits=len(results),
            )
            return results

    # Last resort — search without a locale filter.
    results = await kb_repo.search(db, query, project_id=project_id, limit=limit)
    if results:
        _log.debug("kb.search.cross_locale_hit", query=query, hits=len(results))
    return results


def _locale_fallback(lang: str | None, default_lang: str) -> list[str]:
    """Ordered list of locales to try; no duplicates."""
    chain = [c for c in (lang, default_lang) if c]
    seen: set[str] = set()
    out: list[str] = []
    for c in chain:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out
