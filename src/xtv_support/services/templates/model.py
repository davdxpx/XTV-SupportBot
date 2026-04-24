"""Declarative project template model.

Each :class:`ProjectTemplate` is an immutable bundle. The runner
translates it into Mongo writes at install time; templates never do
I/O themselves, which keeps them trivial to unit-test and to import
from plugins without pulling in pymongo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class MacroSeed:
    name: str
    body: str
    tags: tuple[str, ...] = ()
    team_scope: str | None = None  # None = global


@dataclass(frozen=True, slots=True, kw_only=True)
class KbSeed:
    slug: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    lang: str = "en"


@dataclass(frozen=True, slots=True, kw_only=True)
class RoutingSeed:
    """One routing rule — shape mirrors ``teams/routing.py`` so the template
    runner can insert it directly into the ``teams.routing_rules`` array."""

    match_tag: str | None = None
    match_priority: str | None = None
    match_project_type: str | None = None
    weight: int = 1
    target_team_slug: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SlaOverrides:
    warn_minutes: int | None = None
    breach_minutes: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTemplate:
    """Everything a newborn project needs to feel alive."""

    slug: str
    name: str
    description: str
    icon: str = "📁"
    project_type: str = "support"  # support | feedback | contact

    welcome_card_title: str | None = None
    welcome_card_body: str | None = None

    intake_fields: tuple[str, ...] = ()

    macros: tuple[MacroSeed, ...] = field(default_factory=tuple)
    kb_articles: tuple[KbSeed, ...] = field(default_factory=tuple)
    routing_rules: tuple[RoutingSeed, ...] = field(default_factory=tuple)
    sla_overrides: SlaOverrides | None = None

    csat_enabled: bool = False
    csat_required: bool = False

    default_priority: str = "normal"
    default_tags: tuple[str, ...] = ()

    feature_flag_overrides: tuple[tuple[str, bool], ...] = ()

    post_install_hint: str | None = None
