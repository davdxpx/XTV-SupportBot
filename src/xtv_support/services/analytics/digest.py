"""Weekly analytics digest renderer.

Pure text builder — takes the rollup documents out of
``analytics_daily`` and formats a concise, readable HTML digest the
plugin can paste into the admin forum topic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class DigestPayload:
    """Rendered digest ready to send to Telegram."""

    title: str
    body: str

    @property
    def full_html(self) -> str:
        return f"<b>{self.title}</b>\n\n{self.body}".strip()


def _fmt_seconds(s: float | None) -> str:
    if s is None:
        return "—"
    if s < 60:
        return f"{int(s)}s"
    if s < 3600:
        return f"{int(s / 60)}m"
    return f"{s / 3600:.1f}h"


def _fmt_ratio(r: float) -> str:
    return f"{int(round(r * 100))}%"


def render(
    rollups: Iterable[Mapping],
    *,
    for_range: str = "last 7 days",
) -> DigestPayload:
    """Aggregate a week's worth of rollup docs into one digest."""
    docs = [d for d in rollups if isinstance(d, Mapping)]
    if not docs:
        return DigestPayload(
            title=f"📊 Analytics digest — {for_range}",
            body="<i>No tickets in this window.</i>",
        )

    total = sum(int(d.get("total", 0)) for d in docs)
    breached = sum(int(d.get("sla_breached", 0)) for d in docs)
    sla_total = sum(int(d.get("sla_total", 0)) for d in docs)
    ratio = 1.0 if sla_total == 0 else 1 - (breached / sla_total)

    # Averages weighted by sample count; medians don't combine cleanly
    # but a weighted mean gives operators a directional number.
    frt_vals: list[float] = []
    res_vals: list[float] = []
    for d in docs:
        v = d.get("first_response_median")
        if isinstance(v, (int, float)):
            frt_vals.append(float(v))
        v = d.get("resolution_median")
        if isinstance(v, (int, float)):
            res_vals.append(float(v))
    frt_avg = None if not frt_vals else sum(frt_vals) / len(frt_vals)
    res_avg = None if not res_vals else sum(res_vals) / len(res_vals)

    # Top-3 projects + teams by aggregated volume.
    by_project: dict[str, int] = {}
    by_team: dict[str, int] = {}
    for d in docs:
        for k, v in (d.get("by_project") or {}).items():
            by_project[str(k)] = by_project.get(str(k), 0) + int(v)
        for k, v in (d.get("by_team") or {}).items():
            by_team[str(k)] = by_team.get(str(k), 0) + int(v)

    top_projects = sorted(by_project.items(), key=lambda x: -x[1])[:3]
    top_teams = sorted(by_team.items(), key=lambda x: -x[1])[:3]

    lines: list[str] = [
        f"<b>Tickets</b>: {total}",
        f"<b>SLA compliance</b>: {_fmt_ratio(ratio)} ({sla_total - breached}/{sla_total} met)",
        f"<b>First response</b> median avg: {_fmt_seconds(frt_avg)}",
        f"<b>Resolution</b> median avg: {_fmt_seconds(res_avg)}",
    ]
    if top_projects:
        lines.append("")
        lines.append("<b>Top projects</b>:")
        lines.extend(
            f"  • <code>{slug}</code> — {count}" for slug, count in top_projects
        )
    if top_teams:
        lines.append("")
        lines.append("<b>Top teams</b>:")
        lines.extend(
            f"  • <code>{slug}</code> — {count}" for slug, count in top_teams
        )

    return DigestPayload(
        title=f"📊 Analytics digest — {for_range}",
        body="\n".join(lines),
    )
