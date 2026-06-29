"""Templates for the External User Directory setup wizard.

This module separates the copy and layout of the interactive setup wizard
from the control flow in the handlers module.
"""

from __future__ import annotations

from typing import Any

from xtv_support.ui.primitives.panel import Panel, PanelButton, StatTile


# ---------------------------------------------------------------------------
# Step 0: Entry / Landing
# ---------------------------------------------------------------------------
def render_entry_card(config_exists: bool, config: dict[str, Any] | None = None) -> Panel:
    """The landing card for the External User Directory setup."""
    if not config_exists:
        return Panel(
            title="🔌 External User Directory",
            subtitle="Connect your own database",
            body=(
                "Connect SupportBot to your own product's user database so VIP or "
                "important users can be detected automatically and prioritized accordingly.",
                "",
                "This is fully optional and <b>read-only</b> — SupportBot will never "
                "write to your database.",
            ),
            action_rows=(
                (PanelButton(label="🚀 Start setup", callback="cb:v2:admin:extdir:wizard:start"),),
                (PanelButton(label="◀ Back", callback="cb:v2:admin:section:home"),),
            ),
        )

    # Config exists
    cfg = config or {}
    status = "✅ Enabled" if cfg.get("enabled", True) else "⏸ Disabled"
    db_name = cfg.get("database_name", "unknown")
    col_name = cfg.get("collection_name", "unknown")
    last_verified = cfg.get("last_verified_at", "Never")

    return Panel(
        title="🔌 External User Directory",
        subtitle=f"Status: {status}",
        stats=(
            StatTile(label="Database", value=db_name),
            StatTile(label="Collection", value=col_name),
            StatTile(label="Last Verified", value=str(last_verified)),
        ),
        action_rows=(
            (
                PanelButton(label="🔧 Reconfigure", callback="cb:v2:admin:extdir:wizard:start"),
                PanelButton(
                    label="⏸ Disable" if status == "✅ Enabled" else "▶ Enable",
                    callback="cb:v2:admin:extdir:toggle",
                ),
            ),
            (PanelButton(label="🗑 Delete entirely", callback="cb:v2:admin:extdir:delete"),),
            (PanelButton(label="◀ Back", callback="cb:v2:admin:section:home"),),
        ),
    )


# ---------------------------------------------------------------------------
# Wizard Steps (1-3): Connection info
# ---------------------------------------------------------------------------
def get_uri_prompt() -> tuple[str, list[list[dict[str, str]]]]:
    text = (
        "<b>Step 1/7: Connection String</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Please send the raw MongoDB connection URI for your database.\n\n"
        "<i>Security note: This will be encrypted at rest and never logged. "
        "SupportBot will delete your message containing the URI immediately after reading it.</i>\n\n"
        "Send the URI below, or /cancel to abort."
    )
    return text, [[{"label": "❌ Cancel", "callback": "cb:v2:admin:extdir:wizard:cancel"}]]


def get_db_prompt(default_db: str | None) -> tuple[str, list[list[dict[str, str]]]]:
    text = (
        "<b>Step 2/7: Database Name</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Which database should we connect to?\n\n"
        "Send the database name as plain text below, or /cancel to abort."
    )
    kb = []
    if default_db:
        kb.append(
            [
                {
                    "label": f"Use default from URI ({default_db})",
                    "callback": f"cb:v2:admin:extdir:wizard:set_db:{default_db}",
                }
            ]
        )
    kb.append([{"label": "❌ Cancel", "callback": "cb:v2:admin:extdir:wizard:cancel"}])
    return text, kb


def get_collection_prompt() -> tuple[str, list[list[dict[str, str]]]]:
    text = (
        "<b>Step 3/7: Collection Name</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Which collection contains your users?\n\n"
        "<i>(Typically 'users' or 'accounts')</i>\n\n"
        "Send the collection name as plain text below."
    )
    return text, [
        [{"label": "Use 'users'", "callback": "cb:v2:admin:extdir:wizard:set_col:users"}],
        [{"label": "❌ Cancel", "callback": "cb:v2:admin:extdir:wizard:cancel"}],
    ]


# ---------------------------------------------------------------------------
# Step 4: Connection testing
# ---------------------------------------------------------------------------
def render_connection_test_failure(error_msg: str) -> Panel:
    return Panel(
        title="❌ Connection Failed",
        subtitle="Could not reach the database",
        body=(
            f"Error details:\n<code>{error_msg}</code>",
            "",
            "Please check your credentials, network access, and collection name.",
        ),
        action_rows=(
            (
                PanelButton(
                    label="🔗 Try a different URI", callback="cb:v2:admin:extdir:wizard:restart"
                ),
            ),
            (
                PanelButton(
                    label="🗄 Try a different DB name", callback="cb:v2:admin:extdir:wizard:step2"
                ),
            ),
            (
                PanelButton(
                    label="📂 Try a different collection name",
                    callback="cb:v2:admin:extdir:wizard:step3",
                ),
            ),
            (PanelButton(label="❌ Cancel Setup", callback="cb:v2:admin:extdir:wizard:cancel"),),
        ),
    )


# ---------------------------------------------------------------------------
# Step 5: Telegram ID field selection
# ---------------------------------------------------------------------------
def render_field_picker(
    step_num: int,
    title: str,
    subtitle: str,
    fields: list[tuple[str, str]],
    page: int = 1,
    total_pages: int = 1,
) -> Panel:
    """Generic field picker used for ID, expiry, and mapping steps."""
    body_lines = [
        f"<b>{title}</b>",
        f"<i>{subtitle}</i>",
        "",
        "We fetched a sample document. Which field should we use?",
        "",
    ]

    rows = []
    # Maximum 10 fields per page
    per_page = 10
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    for f_path, f_type in fields[start_idx:end_idx]:
        label = f"{f_path} ({f_type})"
        # Callbacks must be short. Use a generic 'pick_field' and stash context in state.
        rows.append(
            (PanelButton(label=label, callback=f"cb:v2:admin:extdir:wizard:pick:{f_path}"),)
        )

    nav_row = []
    if page > 1:
        nav_row.append(
            PanelButton(label="◀ Prev", callback=f"cb:v2:admin:extdir:wizard:page:{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            PanelButton(label="Next ▶", callback=f"cb:v2:admin:extdir:wizard:page:{page + 1}")
        )
    if nav_row:
        rows.append(tuple(nav_row))

    rows.append(
        (
            PanelButton(
                label="⌨️ Type custom field path instead",
                callback="cb:v2:admin:extdir:wizard:custom_field",
            ),
        )
    )
    rows.append((PanelButton(label="❌ Cancel", callback="cb:v2:admin:extdir:wizard:cancel"),))

    return Panel(
        title=f"Step {step_num}/7: Setup Fields",
        subtitle=title,
        body=tuple(body_lines),
        action_rows=tuple(rows),
        page=page if total_pages > 1 else None,
        total_pages=total_pages if total_pages > 1 else None,
    )


# ---------------------------------------------------------------------------
# Step 6: Expiry field
# ---------------------------------------------------------------------------
def render_expiry_prompt() -> Panel:
    return Panel(
        title="Step 6/7: Expiry Field",
        subtitle="Optional user expiration",
        body=(
            "Does your user schema have an expiry or valid-until field?",
            "If configured, users whose expiry date has passed will NOT be treated as VIP.",
        ),
        action_rows=(
            (
                PanelButton(label="✅ Yes", callback="cb:v2:admin:extdir:wizard:has_expiry:yes"),
                PanelButton(label="❌ No", callback="cb:v2:admin:extdir:wizard:has_expiry:no"),
            ),
            (PanelButton(label="◀ Back", callback="cb:v2:admin:extdir:wizard:step5"),),
        ),
    )


# ---------------------------------------------------------------------------
# Step 7: Field Mappings
# ---------------------------------------------------------------------------
def render_mapping_kind_prompt(field_path: str, sample_val: str, py_type: str) -> Panel:
    return Panel(
        title="Step 7/7: Field Interpretation",
        subtitle=f"Mapping field: {field_path}",
        body=(
            f"Sample value: <code>{sample_val}</code> (Type: {py_type})",
            "",
            "How should SupportBot interpret this field?",
        ),
        action_rows=(
            (
                PanelButton(
                    label="✅ Yes/No flag", callback="cb:v2:admin:extdir:wizard:kind:boolean"
                ),
                PanelButton(
                    label="🏷 Category/tier name", callback="cb:v2:admin:extdir:wizard:kind:enum"
                ),
                PanelButton(
                    label="🔢 Number/score",
                    callback="cb:v2:admin:extdir:wizard:kind:numeric_threshold",
                ),
            ),
            (
                PanelButton(
                    label="◀ Back to field selection",
                    callback="cb:v2:admin:extdir:wizard:mapping_loop",
                ),
            ),
        ),
    )


def render_boolean_vip_prompt(field_path: str) -> Panel:
    return Panel(
        title="Boolean Mapping",
        subtitle=field_path,
        body=(
            "Does a value of TRUE mean this user is important/VIP?",
            "(Select No if True means 'is_free_tier' or similar where False = VIP)",
        ),
        action_rows=(
            (
                PanelButton(label="True = VIP", callback="cb:v2:admin:extdir:wizard:bool_vip:true"),
                PanelButton(
                    label="False = VIP", callback="cb:v2:admin:extdir:wizard:bool_vip:false"
                ),
            ),
            (PanelButton(label="◀ Back", callback="cb:v2:admin:extdir:wizard:kind_back"),),
        ),
    )


def render_boolean_local_prompt() -> Panel:
    return Panel(
        title="Local Concept",
        subtitle="What does this flag control?",
        body=("Which local SupportBot concept does this boolean control?"),
        action_rows=(
            (
                PanelButton(
                    label="vip_status", callback="cb:v2:admin:extdir:wizard:bool_local:vip_status"
                ),
                PanelButton(
                    label="display_badge",
                    callback="cb:v2:admin:extdir:wizard:bool_local:display_badge",
                ),
            ),
            (PanelButton(label="◀ Back", callback="cb:v2:admin:extdir:wizard:bool_vip_back"),),
        ),
    )


def render_enum_too_many_prompt(count: int) -> Panel:
    return Panel(
        title="⚠️ Too Many Distinct Values",
        subtitle=f"Found {count} distinct values",
        body=(
            f"This field has {count} different values in your database, which "
            "doesn't look like a small set of tiers or categories.",
            "",
            "Are you sure this is the right field?",
        ),
        action_rows=(
            (
                PanelButton(
                    label="✅ Yes, continue anyway",
                    callback="cb:v2:admin:extdir:wizard:enum_continue",
                ),
                PanelButton(
                    label="❌ No, pick a different field",
                    callback="cb:v2:admin:extdir:wizard:mapping_loop",
                ),
            ),
        ),
    )


def get_enum_order_prompt(distinct_values: list[str]) -> tuple[str, list[list[dict[str, str]]]]:
    vals = "\n".join(f"• <code>{v}</code>" for v in distinct_values)
    text = (
        "<b>Enum Ordering</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"We found the following distinct values:\n{vals}\n\n"
        "Please reply with these values <b>in order from least to most important</b>, "
        "separated by commas or newlines."
    )
    return text, [[{"label": "◀ Back", "callback": "cb:v2:admin:extdir:wizard:kind_back"}]]


def render_enum_vip_prompt(ordered_values: list[str]) -> Panel:
    rows = []
    for val in ordered_values:
        rows.append(
            (
                PanelButton(
                    label=f"From {val} and up", callback=f"cb:v2:admin:extdir:wizard:enum_vip:{val}"
                ),
            )
        )

    rows.append(
        (
            PanelButton(
                label="None are VIP, just track tier",
                callback="cb:v2:admin:extdir:wizard:enum_vip:NONE",
            ),
        )
    )
    rows.append(
        (PanelButton(label="◀ Back", callback="cb:v2:admin:extdir:wizard:enum_order_back"),)
    )

    return Panel(
        title="VIP Threshold",
        subtitle="Enum Tiering",
        body=("Starting from which tier should users be treated as VIP?"),
        action_rows=tuple(rows),
    )


def render_numeric_info_prompt(
    field_path: str, min_val: float, max_val: float
) -> tuple[str, list[list[dict[str, str]]]]:
    text = (
        f"<b>Numeric Mapping</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Values in your database for <code>{field_path}</code> currently range from {min_val} to {max_val}.\n\n"
        "What is the threshold number? Users with a value greater than or equal to this number will be VIP.\n\n"
        "Reply with the threshold number below."
    )
    return text, [[{"label": "◀ Back", "callback": "cb:v2:admin:extdir:wizard:kind_back"}]]


def render_numeric_warning_prompt(thresh: float, min_val: float, max_val: float) -> Panel:
    return Panel(
        title="⚠️ Threshold Outside Range",
        subtitle=f"Threshold: {thresh}",
        body=(
            f"That threshold ({thresh}) is outside the currently observed range ({min_val} to {max_val}).",
            "No users would be marked VIP today. Continue anyway?",
        ),
        action_rows=(
            (
                PanelButton(
                    label="✅ Yes, continue anyway",
                    callback="cb:v2:admin:extdir:wizard:num_continue",
                ),
                PanelButton(
                    label="🔢 Pick a different number",
                    callback="cb:v2:admin:extdir:wizard:num_retry",
                ),
            ),
        ),
    )


def render_field_summary(configured_count: int, summary_text: str) -> Panel:
    return Panel(
        title="Configured so far",
        subtitle=f"{configured_count} field(s) mapped",
        body=(summary_text,),
        action_rows=(
            (
                PanelButton(
                    label="➕ Add another field", callback="cb:v2:admin:extdir:wizard:mapping_loop"
                ),
            ),
            (
                PanelButton(
                    label="✅ I'm done, review & save", callback="cb:v2:admin:extdir:wizard:review"
                ),
            ),
            (PanelButton(label="❌ Cancel Setup", callback="cb:v2:admin:extdir:wizard:cancel"),),
        ),
    )


# ---------------------------------------------------------------------------
# Step 8: Final Review
# ---------------------------------------------------------------------------
def render_final_review(config_summary: str) -> Panel:
    return Panel(
        title="Final Review",
        subtitle="External User Directory Configuration",
        body=(
            "Please review your configuration:",
            "",
            config_summary,
            "",
            "If this looks correct, save and enable the integration.",
        ),
        action_rows=(
            (PanelButton(label="💾 Save & enable", callback="cb:v2:admin:extdir:wizard:save"),),
            (PanelButton(label="🔄 Start over", callback="cb:v2:admin:extdir:wizard:start"),),
            (
                PanelButton(
                    label="❌ Cancel, discard everything",
                    callback="cb:v2:admin:extdir:wizard:cancel",
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Step 9: Success & Testing
# ---------------------------------------------------------------------------
def render_success(admin_id: int) -> Panel:
    return Panel(
        title="✅ Configuration Saved",
        subtitle="Integration is live",
        body=(
            "The External User Directory has been successfully configured and hot-reloaded.",
            "",
            "You can test the lookup right now to verify it works.",
        ),
        action_rows=(
            (
                PanelButton(
                    label="🔎 Test lookup for my own Telegram ID",
                    callback=f"cb:v2:admin:extdir:wizard:test_id:{admin_id}",
                ),
            ),
            (
                PanelButton(
                    label="🔎 Test with a different Telegram ID",
                    callback="cb:v2:admin:extdir:wizard:test_custom",
                ),
            ),
            (PanelButton(label="◀ Back to Admin panel", callback="cb:v2:admin:section:home"),),
        ),
    )


def render_test_result(admin_id: int, result_str: str) -> Panel:
    return Panel(
        title="🔎 Lookup Result",
        subtitle="External DB Test",
        body=(
            result_str,
            "",
            "<i>Note: If looking up your own ID, 'not found' or 'not VIP' is expected unless your account exists there with VIP status.</i>",
        ),
        action_rows=(
            (
                PanelButton(
                    label="🔎 Test with a different Telegram ID",
                    callback="cb:v2:admin:extdir:wizard:test_custom",
                ),
            ),
            (PanelButton(label="◀ Back to Admin panel", callback="cb:v2:admin:section:home"),),
        ),
    )
