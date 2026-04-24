"""CSAT service — pure helpers + DB persistence.

Two public entry points:

* :func:`record_rating` — stores a 1..5 star score in ``csat_responses``
  and publishes :class:`CsatReceived`. Caller side-effects (updating
  ticket, thanking the user) live in the handler.
* :func:`record_comment` — appends a free-text follow-up to an existing
  CSAT record. Publishes :class:`CsatCommented`.
* :func:`aggregate_stats` — rolling N-day aggregate for the admin
  dashboard (avg score, response count, NPS-ish proxy).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import CsatCommented, CsatReceived
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.core.events import EventBus

_log = get_logger("csat")

MIN_SCORE = 1
MAX_SCORE = 5


class InvalidScoreError(ValueError):
    pass


def validate_score(score: int) -> int:
    if not isinstance(score, int) or not (MIN_SCORE <= score <= MAX_SCORE):
        raise InvalidScoreError(
            f"CSAT score must be an integer in [{MIN_SCORE}, {MAX_SCORE}], got {score!r}"
        )
    return score


@dataclass(frozen=True, slots=True)
class CsatStats:
    responses: int
    average: float
    distribution: dict[int, int]  # {1..5: count}
    promoters: int  # score >= 4
    detractors: int  # score <= 2

    @property
    def promoter_share(self) -> float:
        return 0.0 if not self.responses else round(self.promoters / self.responses, 3)


async def record_rating(
    db: AsyncIOMotorDatabase,
    bus: EventBus | None,
    *,
    ticket_id: str,
    user_id: int,
    score: int,
    team_id: str | None = None,
) -> None:
    """Persist a rating + emit event. Duplicate ratings overwrite."""
    validate_score(score)
    doc = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "score": score,
        "team_id": team_id,
        "submitted_at": utcnow(),
    }
    try:
        await db.csat_responses.update_one(
            {"ticket_id": ticket_id, "user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("csat.persist_failed", ticket_id=ticket_id, error=str(exc))
        return

    if bus is not None:
        await bus.publish(
            CsatReceived(
                ticket_id=ticket_id,
                user_id=user_id,
                score=score,
                team_id=team_id,
            )
        )
    _log.info("csat.recorded", ticket_id=ticket_id, score=score)


async def record_comment(
    db: AsyncIOMotorDatabase,
    bus: EventBus | None,
    *,
    ticket_id: str,
    user_id: int,
    comment: str,
) -> None:
    doc = await db.csat_responses.find_one({"ticket_id": ticket_id, "user_id": user_id})
    if doc is None:
        _log.debug(
            "csat.comment_without_rating",
            ticket_id=ticket_id,
            user_id=user_id,
        )
        return
    try:
        await db.csat_responses.update_one(
            {"ticket_id": ticket_id, "user_id": user_id},
            {"$set": {"comment": comment, "commented_at": utcnow()}},
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("csat.comment_persist_failed", error=str(exc))
        return

    if bus is not None:
        await bus.publish(
            CsatCommented(
                ticket_id=ticket_id,
                user_id=user_id,
                score=int(doc.get("score") or 0),
                comment=comment,
            )
        )


async def aggregate_stats(
    db: AsyncIOMotorDatabase,
    *,
    days: int = 30,
    team_id: str | None = None,
) -> CsatStats:
    """Rolling aggregate. Simple counter — no $facet so mongomock works."""
    since = utcnow() - timedelta(days=days)
    query: dict = {"submitted_at": {"$gte": since}}
    if team_id is not None:
        query["team_id"] = team_id

    dist: dict[int, int] = {s: 0 for s in range(MIN_SCORE, MAX_SCORE + 1)}
    total = 0
    score_sum = 0
    promoters = 0
    detractors = 0
    async for doc in db.csat_responses.find(query, projection={"score": 1}):
        score = int(doc.get("score") or 0)
        if score < MIN_SCORE or score > MAX_SCORE:
            continue
        dist[score] += 1
        total += 1
        score_sum += score
        if score >= 4:
            promoters += 1
        if score <= 2:
            detractors += 1

    average = 0.0 if total == 0 else round(score_sum / total, 2)
    return CsatStats(
        responses=total,
        average=average,
        distribution=dist,
        promoters=promoters,
        detractors=detractors,
    )
