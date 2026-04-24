"""Admin control panel — drill-down grid.

``/admin`` now opens a **landing card** with eight big category
tiles in a 2-per-row grid. Tapping a tile doesn't swap tabs — it
replaces the whole card with that section's own dedicated view, which
has its own buttons + a ◀ Admin home back button.

Visual language:

- ``━━━`` horizontal rules frame every card (Panel ``hr=True``).
- Every button + section title carries an emoji so the UI reads at a
  glance instead of being a wall of black text.
- Single-line hints (tips, context) render as ``<blockquote>`` via
  ``Panel.hints``.
"""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.ui.primitives.panel import Panel, PanelButton, StatTile

# ---------------------------------------------------------------------------
# Section keys (callback-data suffix: ``cb:v2:admin:section:<key>``)
# ---------------------------------------------------------------------------
SECTIONS: tuple[tuple[str, str], ...] = (
    ("overview", "📊 Overview"),
    ("tickets", "🎫 Tickets"),
    ("teams", "👥 Teams"),
    ("projects", "📁 Projects"),
    ("rules", "⚡ Automation"),
    ("broadcasts", "📣 Broadcasts"),
    ("analytics", "📈 Analytics"),
    ("settings", "⚙️ Settings"),
)


@dataclass(frozen=True, slots=True)
class OverviewStats:
    open_tickets: int = 0
    sla_at_risk: int = 0
    unassigned: int = 0
    active_agents: int = 0
    total_projects: int = 0
    total_users: int = 0


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
BACK_HOME = PanelButton(label="◀ Admin home", callback="cb:v2:admin:section:home")


def _pair(*buttons: PanelButton) -> tuple[PanelButton, ...]:
    """Syntactic sugar — makes the 2-per-row intent explicit at call sites."""
    return buttons


# ---------------------------------------------------------------------------
# Landing card — /admin opens this
# ---------------------------------------------------------------------------
def render_home(stats: OverviewStats) -> Panel:
    """The big 2×4 drill-down grid."""
    tiles: list[tuple[PanelButton, ...]] = []
    row: list[PanelButton] = []
    for key, label in SECTIONS:
        row.append(PanelButton(label=label, callback=f"cb:v2:admin:section:{key}"))
        if len(row) == 2:
            tiles.append(tuple(row))
            row = []
    if row:
        tiles.append(tuple(row))

    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Home",
        body=(
            f"<b>{stats.open_tickets}</b> open · "
            f"<b>{stats.sla_at_risk}</b> SLA at risk · "
            f"<b>{stats.unassigned}</b> unassigned",
            f"<b>{stats.active_agents}</b> agent(s) online · "
            f"<b>{stats.total_projects}</b> project(s) · "
            f"<b>{stats.total_users}</b> user(s)",
        ),
        hints=(
            "💡 Tap a tile to open that section. Every function is also "
            "reachable as a slash command — see /help.",
        ),
        action_rows=tuple(tiles),
    )


# ---------------------------------------------------------------------------
# Section renderers — each is a self-contained screen with a ◀ back button
# ---------------------------------------------------------------------------
def render_overview_section(stats: OverviewStats) -> Panel:
    return Panel(
        title="📊 Overview",
        subtitle="Live snapshot of your helpdesk",
        stats=(
            StatTile(label="🎫 Open tickets", value=str(stats.open_tickets)),
            StatTile(label="⏰ SLA at risk", value=str(stats.sla_at_risk)),
            StatTile(label="🔓 Unassigned", value=str(stats.unassigned)),
            StatTile(label="👤 Active agents", value=str(stats.active_agents)),
            StatTile(label="📁 Projects", value=str(stats.total_projects)),
            StatTile(label="🙋 Users", value=str(stats.total_users)),
        ),
        hints=("🔄 Numbers refresh on every tab-switch; open a section to drill in.",),
        action_rows=(
            _pair(
                PanelButton(label="📋 Open inbox", callback="cb:v2:admin:open_inbox"),
                PanelButton(label="📣 New broadcast", callback="cb:v2:admin:section:broadcasts"),
            ),
            (BACK_HOME,),
        ),
    )


def render_tickets_section(open_today: int, closed_today: int) -> Panel:
    return Panel(
        title="🎫 Tickets",
        subtitle="Today's activity",
        stats=(
            StatTile(label="📮 Opened today", value=str(open_today)),
            StatTile(label="✅ Closed today", value=str(closed_today)),
        ),
        hints=("📋 /inbox opens the agent cockpit with saved views + bulk actions.",),
        action_rows=(
            _pair(
                PanelButton(label="📋 Agent inbox", callback="cb:v2:admin:open_inbox"),
                PanelButton(label="🔎 Find by ID", callback="cb:v2:admin:find_ticket"),
            ),
            (BACK_HOME,),
        ),
    )


def render_teams_section(num_teams: int, num_members: int) -> Panel:
    return Panel(
        title="👥 Teams",
        subtitle="Who handles what",
        stats=(
            StatTile(label="👥 Teams", value=str(num_teams)),
            StatTile(label="🙋 Total members", value=str(num_members)),
        ),
        hints=("✏️ Pick a team to rename it, set timezone, manage members, or delete.",),
        action_rows=(
            _pair(
                PanelButton(label="📜 Browse teams", callback="cb:v2:admin:teams:list"),
                PanelButton(label="➕ New team", callback="cb:v2:admin:teams:new"),
            ),
            (BACK_HOME,),
        ),
    )


def render_projects_section(num_projects: int) -> Panel:
    return Panel(
        title="📁 Projects",
        subtitle="Intake surfaces",
        stats=(StatTile(label="📁 Active projects", value=str(num_projects)),),
        hints=("🎯 Templates seed macros / KB / routing for you — see /templates.",),
        action_rows=(
            _pair(
                PanelButton(
                    label="🎯 From template",
                    callback="cb:v2:admin:projects:from_template",
                ),
                PanelButton(label="📜 Browse", callback="cb:v2:admin:projects:list"),
            ),
            _pair(
                PanelButton(label="📄 Blank project", callback="cb:v2:admin:projects:blank"),
                BACK_HOME,
            ),
        ),
    )


def render_rules_section(num_rules: int, num_enabled: int) -> Panel:
    return Panel(
        title="⚡ Automation rules",
        subtitle="If-this-then-that over ticket events",
        stats=(
            StatTile(label="📜 Rules", value=str(num_rules)),
            StatTile(label="✅ Enabled", value=str(num_enabled)),
        ),
        hints=("📘 Full rule syntax + worked examples live in the docs.",),
        action_rows=(
            _pair(
                PanelButton(label="➕ New rule", callback="cb:v2:admin:rules:new"),
                PanelButton(label="📜 Browse rules", callback="cb:v2:admin:rules:list"),
            ),
            (BACK_HOME,),
        ),
    )


def render_broadcasts_section() -> Panel:
    return Panel(
        title="📣 Broadcasts",
        subtitle="One-off announcement to all users",
        body=(
            "Broadcasts are pausable and show a live progress card while "
            "sending. Use them sparingly — respect quiet hours.",
        ),
        hints=("⏸ You can pause / resume mid-send from the progress card.",),
        action_rows=(
            _pair(
                PanelButton(
                    label="📣 Start broadcast",
                    callback="cb:v2:admin:broadcast:new",
                ),
                BACK_HOME,
            ),
        ),
    )


def render_analytics_section(days: int, tickets: int, sla_ratio: float) -> Panel:
    ratio_pct = f"{sla_ratio * 100:.1f}%"
    return Panel(
        title="📈 Analytics",
        subtitle=f"Rolling window — last {days} day(s)",
        stats=(
            StatTile(label="🎫 Tickets", value=str(tickets)),
            StatTile(label="🎯 SLA compliance", value=ratio_pct),
        ),
        hints=("📦 Export CSV for BI or run the weekly digest ad-hoc.",),
        action_rows=(
            _pair(
                PanelButton(
                    label="▶ Run digest now",
                    callback="cb:v2:admin:analytics:digest",
                ),
                PanelButton(label="📦 Export CSV", callback="cb:v2:admin:analytics:export"),
            ),
            (BACK_HOME,),
        ),
    )


def render_settings_section(flags_snapshot: list[tuple[str, bool]]) -> Panel:
    body_lines = (
        "Toggle feature flags below. Live toggles are persisted to "
        "<code>admin_overrides</code> — changes apply on the next request.",
    )
    action_rows_list: list[tuple[PanelButton, ...]] = []

    # Flag grid — 2 flags per row for visual parity with the rest.
    pair: list[PanelButton] = []
    for name, enabled in flags_snapshot:
        box = "✅" if enabled else "⬜"
        pair.append(
            PanelButton(
                label=f"{box} {name}",
                callback=f"cb:v2:admin:flag:{name}",
            )
        )
        if len(pair) == 2:
            action_rows_list.append(tuple(pair))
            pair = []
    if pair:
        action_rows_list.append(tuple(pair))

    action_rows_list.append(
        _pair(
            PanelButton(label="🔑 API keys", callback="cb:v2:admin:apikey:list"),
            PanelButton(label="🔒 Rotate secrets", callback="cb:v2:admin:rotate_secrets"),
        )
    )
    action_rows_list.append((BACK_HOME,))

    return Panel(
        title="⚙️ Settings",
        subtitle="Feature flags + secrets",
        body=body_lines,
        hints=("⚠️ Some flags only take effect after a redeploy — label hints below.",),
        action_rows=tuple(action_rows_list),
    )


# ---------------------------------------------------------------------------
# Backwards-compat — keep legacy ``render_*_tab`` names as thin aliases so
# any handler that still imports them (e.g. the tab-switcher callback for
# users mid-session) still works during the transition.
# ---------------------------------------------------------------------------
render_overview = render_overview_section
render_tickets_tab = render_tickets_section
render_teams_tab = render_teams_section
render_projects_tab = render_projects_section
render_rules_tab = render_rules_section
render_broadcasts_tab = render_broadcasts_section
render_analytics_tab = render_analytics_section
render_settings_tab = render_settings_section

# Older callers imported ``TABS``; expose the new ``SECTIONS`` under that
# name too to avoid breaking imports during the rename window.
TABS = SECTIONS
