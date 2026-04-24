"""Admin control panel — tabbed Panel renderer.

Tabs:

    Overview | Tickets | Teams | Projects | Rules | Broadcasts |
    Analytics | Settings

Each tab reuses :class:`~xtv_support.ui.primitives.panel.Panel` so the
whole panel fits in one Telegram message and tab-switches are in-place
edits (no scroll spam).
"""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.ui.primitives.panel import Panel, PanelButton, StatTile, Tab

TABS: tuple[tuple[str, str], ...] = (
    ("overview", "Overview"),
    ("tickets", "Tickets"),
    ("teams", "Teams"),
    ("projects", "Projects"),
    ("rules", "Rules"),
    ("broadcasts", "Broadcasts"),
    ("analytics", "Analytics"),
    ("settings", "Settings"),
)


@dataclass(frozen=True, slots=True)
class OverviewStats:
    open_tickets: int = 0
    sla_at_risk: int = 0
    unassigned: int = 0
    active_agents: int = 0
    total_projects: int = 0
    total_users: int = 0


def _tabs(active: str) -> tuple[Tab, ...]:
    return tuple(
        Tab(
            key=key,
            label=label,
            callback=f"cb:v2:admin:tab:{key}",
            active=(key == active),
        )
        for key, label in TABS
    )


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------
def render_overview(stats: OverviewStats) -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Overview",
        tabs=_tabs("overview"),
        stats=(
            StatTile(label="Open tickets", value=str(stats.open_tickets)),
            StatTile(label="SLA at risk", value=str(stats.sla_at_risk)),
            StatTile(label="Unassigned", value=str(stats.unassigned)),
            StatTile(label="Active agents", value=str(stats.active_agents)),
            StatTile(label="Projects", value=str(stats.total_projects)),
            StatTile(label="Users", value=str(stats.total_users)),
        ),
        action_rows=(
            (
                PanelButton(label="📋 Open inbox", callback="cb:v2:admin:open_inbox"),
                PanelButton(label="📢 New broadcast", callback="cb:v2:admin:tab:broadcasts"),
            ),
        ),
        footer="<i>Switch tabs with the buttons above.</i>",
    )


def render_tickets_tab(open_today: int, closed_today: int) -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Tickets",
        tabs=_tabs("tickets"),
        stats=(
            StatTile(label="Opened today", value=str(open_today)),
            StatTile(label="Closed today", value=str(closed_today)),
        ),
        action_rows=(
            (PanelButton(label="📋 Agent inbox", callback="cb:v2:admin:open_inbox"),),
            (PanelButton(label="🔎 Find ticket by ID", callback="cb:v2:admin:find_ticket"),),
        ),
        footer="<i>/inbox opens the agent cockpit with saved views + bulk actions.</i>",
    )


def render_teams_tab(num_teams: int, num_members: int) -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Teams",
        tabs=_tabs("teams"),
        stats=(
            StatTile(label="Teams", value=str(num_teams)),
            StatTile(label="Total members", value=str(num_members)),
        ),
        action_rows=(
            (
                PanelButton(label="📜 Browse teams", callback="cb:v2:admin:teams:list"),
                PanelButton(label="➕ New team", callback="cb:v2:admin:teams:new"),
            ),
        ),
        footer="<i>Tap a team to rename / change timezone / manage members / delete.</i>",
    )


def render_projects_tab(num_projects: int) -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Projects",
        tabs=_tabs("projects"),
        stats=(StatTile(label="Active projects", value=str(num_projects)),),
        action_rows=(
            (
                PanelButton(
                    label="📁 Create from template", callback="cb:v2:admin:projects:from_template"
                ),
            ),
            (PanelButton(label="📜 List projects", callback="cb:v2:admin:projects:list"),),
            (PanelButton(label="📄 Blank project", callback="cb:v2:admin:projects:blank"),),
        ),
        footer="<i>/templates lists available seed bundles.</i>",
    )


def render_rules_tab(num_rules: int, num_enabled: int) -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Automation rules",
        tabs=_tabs("rules"),
        stats=(
            StatTile(label="Rules", value=str(num_rules)),
            StatTile(label="Enabled", value=str(num_enabled)),
        ),
        action_rows=(
            (PanelButton(label="➕ New rule", callback="cb:v2:admin:rules:new"),),
            (PanelButton(label="📜 Browse rules", callback="cb:v2:admin:rules:list"),),
        ),
        footer="<i>Rules engine lands in Phase 4.6 — builder UI follows.</i>",
    )


def render_broadcasts_tab() -> Panel:
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Broadcasts",
        tabs=_tabs("broadcasts"),
        body=(
            "Start a broadcast from the admin DM with <code>/broadcast</code>. ",
            "Pause / resume via the progress card.",
        ),
        action_rows=(
            (PanelButton(label="📢 Start broadcast", callback="cb:v2:admin:broadcast:new"),),
        ),
    )


def render_analytics_tab(days: int, tickets: int, sla_ratio: float) -> Panel:
    ratio_pct = f"{sla_ratio * 100:.1f}%"
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle=f"Analytics (last {days}d)",
        tabs=_tabs("analytics"),
        stats=(
            StatTile(label="Tickets", value=str(tickets)),
            StatTile(label="SLA compliance", value=ratio_pct),
        ),
        action_rows=(
            (PanelButton(label="▶ Run digest now", callback="cb:v2:admin:analytics:digest"),),
            (PanelButton(label="📦 Export CSV", callback="cb:v2:admin:analytics:export"),),
        ),
    )


def render_settings_tab(flags_snapshot: list[tuple[str, bool]]) -> Panel:
    body_lines: list[str] = ["Toggle feature flags below. Changes apply on next request."]
    action_rows_list: list[tuple[PanelButton, ...]] = []
    for name, enabled in flags_snapshot:
        box = "✅" if enabled else "⬜"
        action_rows_list.append(
            (PanelButton(label=f"{box} {name}", callback=f"cb:v2:admin:flag:{name}"),)
        )
    action_rows_list.append(
        (
            PanelButton(label="🔑 API keys", callback="cb:v2:admin:apikey:list"),
            PanelButton(label="🔒 Rotate secrets", callback="cb:v2:admin:rotate_secrets"),
        )
    )
    return Panel(
        title="⚙️ Admin Control Panel",
        subtitle="Settings",
        tabs=_tabs("settings"),
        body=tuple(body_lines),
        action_rows=tuple(action_rows_list),
    )
