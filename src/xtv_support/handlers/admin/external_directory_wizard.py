"""Admin handler for the External User Directory Setup Wizard.

This module uses ``ask_and_confirm`` purely for text capture, while
accumulating the in-progress configuration via the FSM data bag.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from xtv_support.config.settings import settings
from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db.external_directory_config import clear_config as delete_config
from xtv_support.infrastructure.db.external_directory_config import get_config, save_config
from xtv_support.infrastructure.db.external_directory_secrets import store_secret_uri
from xtv_support.services.external_directory.connection_manager import ExternalConnectionManager
from xtv_support.services.external_directory.model import (
    EnumRankMapping,
    ExternalDirectoryConfig,
    FieldKind,
    FieldMapping,
)
from xtv_support.ui.primitives import ask_and_confirm as akc
from xtv_support.ui.templates import external_directory_wizard as tpl
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:

    from xtv_support.core.context import HandlerContext

log = get_logger("admin.extdir_wizard")


# ---------------------------------------------------------------------------
# State & Helpers
# ---------------------------------------------------------------------------


async def _edit_panel(client: Client, user_id: int, message_id: int | None, panel: Any) -> None:
    from pyrogram.enums import ParseMode
    from pyrogram.errors import MessageNotModified
    text, kb = panel.render()
    if message_id:
        try:
            await client.edit_message_text(chat_id=user_id, message_id=message_id, text=text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        await client.send_message(user_id, text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)

async def _send_or_edit_panel(client: Client, message: Message | None, cq: CallbackQuery | None, panel: Any) -> None:
    from pyrogram.enums import ParseMode
    from pyrogram.errors import MessageNotModified

    text, kb = panel.render()
    if cq is not None and cq.message is not None:
        try:
            await cq.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        except MessageNotModified:
            pass
        finally:
            await cq.answer()
    elif message is not None:
        await client.send_message(
            message.chat.id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )

# Base StateMachine state
WIZARD_STATE = "extdir_wizard"

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

async def reload_provider(ctx: HandlerContext) -> None:
    """Hot-reload the DirectoryProvider in the dependency container."""
    from xtv_support.services.external_directory.factory import (
        DirectoryProviderLike,
        build_provider,
    )
    provider = await build_provider(ctx.db)
    ctx.container.register_instance(DirectoryProviderLike, provider, override=True)


# We will populate these with handlers later.
handlers = []

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@Client.on_callback_query(filters.regex(r"^cb:v2:admin:extdir:(?!wizard:)(.*?)$"), group=HandlerGroup.COMMAND)
async def extdir_callback(client: Client, cq: CallbackQuery) -> None:
    if not cq.from_user or not is_admin(cq.from_user.id):
        await cq.answer("Admin only.", show_alert=True)
        return

    ctx = get_context(client)
    user_id = cq.from_user.id
    data = (cq.data or "").split("cb:v2:admin:extdir:")[1]

    # 0. Entry
    if data == "entry":
        config = await get_config(ctx.db)
        if config:
            from dataclasses import asdict
            panel = tpl.render_entry_card(True, asdict(config))
        else:
            panel = tpl.render_entry_card(False)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    # Delete entirely
    if data == "delete":
        await delete_config(ctx.db)
        await reload_provider(ctx)
        panel = tpl.render_entry_card(False)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        await cq.answer("Configuration deleted.", show_alert=True)
        return

    # Toggle (enable/disable)
    if data == "toggle":
        config = await get_config(ctx.db)
        if config:
            from dataclasses import replace
            new_config = replace(config, enabled=not config.enabled)
            await save_config(ctx.db, new_config)
            await reload_provider(ctx)
            from dataclasses import asdict
            panel = tpl.render_entry_card(True, asdict(new_config))
            await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
            await cq.answer(f"Config {'enabled' if new_config.enabled else 'disabled'}.")
        return

    # Cancel
    if data == "wizard:cancel":
        await ctx.state.clear(user_id)
        from xtv_support.ui.templates.admin_panel import OverviewStats, render_home
        panel = render_home(OverviewStats())
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    # Start (Step 1)
    if data == "wizard:start" or data == "wizard:restart":
        await ctx.state.set(user_id, WIZARD_STATE, data={}, ttl_seconds=3600)
        text, kb_spec = tpl.get_uri_prompt()
        await akc.ask(
            client,
            ctx.db,
            chat_id=user_id,
            user_id=user_id,
            text=text,
            context="extdir_uri",
            args={},
            keyboard=None, # Will render below
            edit_message_id=cq.message.id if cq.message else None,
        )
        return

    # Render AKC inline keyboards properly by passing InlineKeyboardMarkup
    # Not using standard panel render here since ask() needs text and markup separately.
    pass

# Note: We need a small helper to convert row_specs to InlineKeyboardMarkup
def _make_kb(specs):
    if not specs:
        return None
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for row in specs:
        r = []
        for cell in row:
            r.append(InlineKeyboardButton(cell["label"], callback_data=cell["callback"]))
        rows.append(r)
    return InlineKeyboardMarkup(rows)


# Replace the start handler with proper kb
@Client.on_callback_query(filters.regex(r"^cb:v2:admin:extdir:wizard:(.*?)$"), group=HandlerGroup.COMMAND)
async def extdir_wizard_callback(client: Client, cq: CallbackQuery) -> None:
    if not cq.from_user or not is_admin(cq.from_user.id):
        return

    ctx = get_context(client)
    user_id = cq.from_user.id
    cmd = (cq.data or "").split("cb:v2:admin:extdir:wizard:")[1]

    # -----------------------------------------------------------------------
    # Step 2: Database Name
    # -----------------------------------------------------------------------
    if cmd == "step2":
        fsm_data = await ctx.state.data(user_id)
        uri = fsm_data.get("extdir_uri")
        if not uri:
            await cq.answer("Missing URI. Please restart.", show_alert=True)
            return

        import urllib.parse
        parsed = urllib.parse.urlparse(uri)
        default_db = parsed.path.lstrip("/") if parsed.path else None

        text, kb_spec = tpl.get_db_prompt(default_db)
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_db", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    if cmd.startswith("set_db:"):
        db_name = cmd.split(":", 1)[1]
        await ctx.state.merge_data(user_id, extdir_db=db_name)
        text, kb_spec = tpl.get_collection_prompt()
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_col", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    # -----------------------------------------------------------------------
    # Step 3: Collection Name
    # -----------------------------------------------------------------------
    if cmd == "step3":
        text, kb_spec = tpl.get_collection_prompt()
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_col", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    if cmd.startswith("set_col:"):
        col_name = cmd.split(":", 1)[1]
        await ctx.state.merge_data(user_id, extdir_col=col_name)
        # Proceed to step 4
        await _run_test_connection(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    # -----------------------------------------------------------------------
    # Step 5: Telegram ID field (invoked after connection test success)
    # -----------------------------------------------------------------------
    if cmd == "step5":
        await _render_field_picker_for_step(client, cq.message.id if cq.message else None, ctx, user_id, step="id")
        return

    if cmd.startswith("pick:"):
        field_path = cmd.split(":", 1)[1]
        fsm_data = await ctx.state.data(user_id)
        current_step = fsm_data.get("current_step")

        if current_step == "id":
            await ctx.state.merge_data(user_id, extdir_id_field=field_path)
            # Check if this field's sample is string
            doc = fsm_data.get("sample_doc", {})
            val = doc.get(field_path)
            is_string = isinstance(val, str)
            await ctx.state.merge_data(user_id, extdir_id_is_string=is_string)

            # Go to step 6 (Expiry)
            panel = tpl.render_expiry_prompt()
            await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)

        elif current_step == "expiry":
            await ctx.state.merge_data(user_id, extdir_expiry_field=field_path)
            # Go to step 7 (Mapping loop)
            await _render_field_summary_step(client, cq.message.id if cq.message else None, ctx, user_id)

        elif current_step == "mapping":
            await ctx.state.merge_data(user_id, current_mapping_field=field_path)
            doc = fsm_data.get("sample_doc", {})
            # For simplicity, extract value (handling basic nested)
            parts = field_path.split(".")
            val = doc
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
            py_type = type(val).__name__ if val is not None else "Unknown"
            panel = tpl.render_mapping_kind_prompt(field_path, str(val), py_type)
            await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)

        return

    # -----------------------------------------------------------------------
    # Custom Field escape hatch
    # -----------------------------------------------------------------------
    if cmd == "custom_field":
        text = "Please send the exact field path (e.g., `user.telegram.id`)."
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_custom_field", args={}, edit_message_id=cq.message.id if cq.message else None)
        return

    # -----------------------------------------------------------------------
    # Step 6: Expiry flow
    # -----------------------------------------------------------------------
    if cmd.startswith("has_expiry:"):
        ans = cmd.split(":", 1)[1]
        if ans == "no":
            await ctx.state.merge_data(user_id, extdir_expiry_field=None)
            await _render_field_summary_step(client, cq.message.id if cq.message else None, ctx, user_id)
        else:
            await _render_field_picker_for_step(client, cq.message.id if cq.message else None, ctx, user_id, step="expiry")
        return

    # -----------------------------------------------------------------------
    # Step 7: Mapping Loop
    # -----------------------------------------------------------------------
    if cmd == "mapping_loop":
        await _render_field_picker_for_step(client, cq.message.id if cq.message else None, ctx, user_id, step="mapping")
        return

    if cmd == "kind_back":
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        doc = fsm_data.get("sample_doc", {})
        val = doc.get(field_path, "None")
        py_type = type(val).__name__
        panel = tpl.render_mapping_kind_prompt(field_path, str(val), py_type)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    # BOOLEAN
    if cmd == "kind:boolean":
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        panel = tpl.render_boolean_vip_prompt(field_path)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    if cmd.startswith("bool_vip:"):
        ans = cmd.split(":", 1)[1]
        await ctx.state.merge_data(user_id, temp_bool_vip=(ans == "true"))
        panel = tpl.render_boolean_local_prompt()
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    if cmd == "bool_vip_back":
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        panel = tpl.render_boolean_vip_prompt(field_path)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    if cmd.startswith("bool_local:"):
        local_name = cmd.split(":", 1)[1]
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        is_vip = fsm_data.get("temp_bool_vip", True)

        mapping = {
            "local_name": local_name,
            "external_field_path": field_path,
            "kind": "boolean",
            "boolean_true_means_vip": is_vip
        }

        mappings = list(fsm_data.get("extdir_mappings", []))
        mappings.append(mapping)
        await ctx.state.merge_data(user_id, extdir_mappings=mappings)
        await _render_field_summary_step(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    # ENUM
    if cmd == "kind:enum":
        # Run distinct query
        await _run_enum_distinct_query(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    if cmd == "enum_continue":
        fsm_data = await ctx.state.data(user_id)
        distinct_vals = fsm_data.get("temp_enum_vals", [])
        text, kb_spec = tpl.get_enum_order_prompt(distinct_vals)
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_enum_order", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    if cmd == "enum_order_back":
        fsm_data = await ctx.state.data(user_id)
        distinct_vals = fsm_data.get("temp_enum_vals", [])
        text, kb_spec = tpl.get_enum_order_prompt(distinct_vals)
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_enum_order", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    if cmd.startswith("enum_vip:"):
        vip_thresh = cmd.split(":", 1)[1]
        fsm_data = await ctx.state.data(user_id)
        ordered_vals = fsm_data.get("temp_ordered_vals", [])
        field_path = fsm_data.get("current_mapping_field")

        enum_mappings = []
        is_vip_flag = False
        for i, val in enumerate(ordered_vals):
            if val == vip_thresh:
                is_vip_flag = True
            enum_mappings.append({
                "raw_value": val,
                "rank_label": val.capitalize(),
                "rank_order": i,
                "is_vip": is_vip_flag if vip_thresh != "NONE" else False
            })

        mapping = {
            "local_name": "tier_label",
            "external_field_path": field_path,
            "kind": "enum",
            "enum_mapping": enum_mappings
        }

        mappings = list(fsm_data.get("extdir_mappings", []))
        mappings.append(mapping)
        await ctx.state.merge_data(user_id, extdir_mappings=mappings)
        await _render_field_summary_step(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    # NUMERIC
    if cmd == "kind:numeric_threshold":
        await _run_numeric_minmax_query(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    if cmd == "num_retry":
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        min_val = fsm_data.get("temp_num_min", 0)
        max_val = fsm_data.get("temp_num_max", 0)
        text, kb_spec = tpl.render_numeric_info_prompt(field_path, min_val, max_val)
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_numeric_thresh", keyboard=_make_kb(kb_spec), edit_message_id=cq.message.id if cq.message else None)
        return

    if cmd == "num_continue":
        fsm_data = await ctx.state.data(user_id)
        field_path = fsm_data.get("current_mapping_field")
        thresh = fsm_data.get("temp_num_thresh", 0)

        mapping = {
            "local_name": "priority_score",
            "external_field_path": field_path,
            "kind": "numeric_threshold",
            "numeric_vip_threshold": thresh
        }

        mappings = list(fsm_data.get("extdir_mappings", []))
        mappings.append(mapping)
        await ctx.state.merge_data(user_id, extdir_mappings=mappings)
        await _render_field_summary_step(client, cq.message.id if cq.message else None, ctx, user_id)
        return

    # -----------------------------------------------------------------------
    # Step 8: Final Review
    # -----------------------------------------------------------------------
    if cmd == "review":
        fsm_data = await ctx.state.data(user_id)
        uri = fsm_data.get("extdir_uri")
        db_name = fsm_data.get("extdir_db")
        col_name = fsm_data.get("extdir_col")
        id_field = fsm_data.get("extdir_id_field")
        expiry = fsm_data.get("extdir_expiry_field")
        mappings = fsm_data.get("extdir_mappings", [])

        lines = [
            f"<b>Database:</b> {db_name}",
            f"<b>Collection:</b> {col_name}",
            f"<b>Telegram ID Field:</b> {id_field}",
            f"<b>Expiry Field:</b> {expiry if expiry else 'None'}",
            "",
            "<b>Field Mappings:</b>"
        ]

        for i, m in enumerate(mappings):
            if m["kind"] == "boolean":
                lines.append(f"{i+1}. <code>{m['external_field_path']}</code> (Boolean) ➡️ <code>{m['local_name']}</code> (True = VIP: {m['boolean_true_means_vip']})")
            elif m["kind"] == "enum":
                lines.append(f"{i+1}. <code>{m['external_field_path']}</code> (Enum) ➡️ <code>{m['local_name']}</code> ({len(m['enum_mapping'])} tiers)")
            elif m["kind"] == "numeric_threshold":
                lines.append(f"{i+1}. <code>{m['external_field_path']}</code> (Numeric) ➡️ <code>{m['local_name']}</code> (VIP Threshold: {m['numeric_vip_threshold']})")

        if not mappings:
            lines.append("<i>No additional mappings configured.</i>")

        panel = tpl.render_final_review("\n".join(lines))
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    if cmd == "save":
        fsm_data = await ctx.state.data(user_id)

        uri = fsm_data.get("extdir_uri")
        db_name = fsm_data.get("extdir_db")
        col_name = fsm_data.get("extdir_col")
        id_field = fsm_data.get("extdir_id_field")
        id_is_string = fsm_data.get("extdir_id_is_string", False)
        expiry = fsm_data.get("extdir_expiry_field")
        raw_mappings = fsm_data.get("extdir_mappings", [])

        mappings = []
        for rm in raw_mappings:
            if rm["kind"] == "enum":
                er_mappings = []
                for em in rm.get("enum_mapping", []):
                    er_mappings.append(EnumRankMapping(
                        raw_value=em["raw_value"],
                        rank_label=em["rank_label"],
                        rank_order=em["rank_order"],
                        is_vip=em["is_vip"]
                    ))
                mappings.append(FieldMapping(
                    local_name=rm["local_name"],
                    external_field_path=rm["external_field_path"],
                    kind=FieldKind(rm["kind"]),
                    enum_mapping=tuple(er_mappings)
                ))
            else:
                mappings.append(FieldMapping(
                    local_name=rm["local_name"],
                    external_field_path=rm["external_field_path"],
                    kind=FieldKind(rm["kind"]),
                    numeric_vip_threshold=rm.get("numeric_vip_threshold"),
                    boolean_true_means_vip=rm.get("boolean_true_means_vip", True)
                ))

        # We must generate a URI ref and store it via Prompt 2's store_secret_uri
        import uuid
        ref = f"extdir_mongo_{uuid.uuid4().hex[:8]}"
        await store_secret_uri(ctx.db, ref, uri)

        config = ExternalDirectoryConfig(
            enabled=True,
            connection_uri_ref=ref,
            database_name=db_name,
            collection_name=col_name,
            external_id_field=id_field,
            external_id_is_string=id_is_string,
            expiry_field_path=expiry,
            field_mappings=tuple(mappings),
            last_verified_at=utcnow(),
            last_verification_error=None
        )

        await save_config(ctx.db, config)
        await reload_provider(ctx)

        await ctx.state.clear(user_id)

        panel = tpl.render_success(user_id)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    # -----------------------------------------------------------------------
    # Step 9: Testing
    # -----------------------------------------------------------------------
    if cmd.startswith("test_id:"):
        tid = int(cmd.split(":", 1)[1])
        # Call provider directly
        from xtv_support.services.external_directory.factory import DirectoryProviderLike
        provider = ctx.container.resolve(DirectoryProviderLike)
        try:
            signal = await provider.get_signal(tid)
            res = (
                f"<b>Resolved Signal for {tid}:</b>\n"
                f"VIP: {signal.is_vip}\n"
                f"Tier: {signal.tier_label} (Rank: {signal.tier_rank_order})\n"
                f"Priority Score: {signal.priority_score}\n"
                f"Display Badge: {signal.display_badge}\n"
                f"Source: {signal.source}"
            )
        except Exception as e:
            res = f"Error performing lookup: {str(e)}"

        panel = tpl.render_test_result(user_id, res)
        await _edit_panel(client, user_id, cq.message.id if cq.message else None, panel)
        return

    if cmd == "test_custom":
        text = "Please send the Telegram ID you wish to test as a number."
        await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_test_id", args={}, edit_message_id=cq.message.id if cq.message else None)
        return


# ---------------------------------------------------------------------------
# Helper functions for heavy queries
# ---------------------------------------------------------------------------

async def _run_test_connection(client: Client, message_id: int | None, ctx: HandlerContext, user_id: int):
    """Step 4 execution."""
    fsm_data = await ctx.state.data(user_id)
    uri = fsm_data.get("extdir_uri")
    db_name = fsm_data.get("extdir_db")
    col_name = fsm_data.get("extdir_col")

    if not uri or not db_name or not col_name:
        return

    cm = ExternalConnectionManager()
    error_msg = None
    try:
        await cm.test_connection(uri, db_name, col_name)
    except Exception as e:
        error_msg = str(e)

    if error_msg:
        panel = tpl.render_connection_test_failure(error_msg)

        # We need CQ simulation if message_id exists to send_or_edit
        await _edit_panel(client, user_id, message_id, panel)
        return

    # Success, run sample query
    client_db = cm.get_db(uri, db_name)
    doc = await client_db[col_name].find_one({})
    if not doc:
        doc = {"_id": "NO_DOCUMENTS_FOUND_IN_COLLECTION"}

    # Store doc
    from bson import ObjectId
    # Clean up for json storage
    clean_doc = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            clean_doc[k] = str(v)
        else:
            clean_doc[k] = v

    await ctx.state.merge_data(user_id, sample_doc=clean_doc)

    # Go to step 5
    await _render_field_picker_for_step(client, message_id, ctx, user_id, step="id")

async def _render_field_picker_for_step(client: Client, message_id: int | None, ctx: HandlerContext, user_id: int, step: str, page: int = 1):
    fsm_data = await ctx.state.data(user_id)
    await ctx.state.merge_data(user_id, current_step=step)

    doc = fsm_data.get("sample_doc", {})
    fields = []

    def extract_fields(d, prefix="", depth=0):
        if depth >= 2:
            return
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            t_name = type(v).__name__
            fields.append((path, t_name))
            if isinstance(v, dict):
                extract_fields(v, path, depth + 1)

    extract_fields(doc)

    # Filter
    if step == "mapping":
        id_field = fsm_data.get("extdir_id_field")
        expiry_field = fsm_data.get("extdir_expiry_field")
        used = [m["external_field_path"] for m in fsm_data.get("extdir_mappings", [])]
        fields = [f for f in fields if f[0] != id_field and f[0] != expiry_field and f[0] not in used]
    elif step == "expiry":
        id_field = fsm_data.get("extdir_id_field")
        fields = [f for f in fields if f[0] != id_field and (f[1] in ("int", "float", "str"))]

    total_pages = max(1, (len(fields) + 9) // 10)

    titles = {
        "id": ("Telegram ID Field", "Which field in your collection holds the Telegram user ID?"),
        "expiry": ("Expiry Field", "Which field holds the user's expiration date or timestamp?"),
        "mapping": ("Field Mappings", "Which field would you like to map to SupportBot?")
    }

    panel = tpl.render_field_picker(
        step_num={"id": 5, "expiry": 6, "mapping": 7}[step],
        title=titles[step][0],
        subtitle=titles[step][1],
        fields=fields,
        page=page,
        total_pages=total_pages
    )

    await _edit_panel(client, user_id, message_id, panel)


async def _render_field_summary_step(client: Client, message_id: int | None, ctx: HandlerContext, user_id: int):
    fsm_data = await ctx.state.data(user_id)
    mappings = fsm_data.get("extdir_mappings", [])

    lines = []
    for m in mappings:
        kind = m.get("kind")
        if kind == "boolean":
            lines.append(f"✅ {m['local_name']} from {m['external_field_path']} (boolean)")
        elif kind == "enum":
            c = len(m.get("enum_mapping", []))
            lines.append(f"✅ {m['local_name']} from {m['external_field_path']} (enum, {c} tiers)")
        elif kind == "numeric_threshold":
            lines.append(f"✅ {m['local_name']} from {m['external_field_path']} (numeric)")

    summary_text = "\n".join(lines) if lines else "No mappings added yet."
    panel = tpl.render_field_summary(len(mappings), summary_text)

    await _edit_panel(client, user_id, message_id, panel)

async def _run_enum_distinct_query(client: Client, message_id: int | None, ctx: HandlerContext, user_id: int):
    fsm_data = await ctx.state.data(user_id)
    uri = fsm_data.get("extdir_uri")
    db_name = fsm_data.get("extdir_db")
    col_name = fsm_data.get("extdir_col")
    field_path = fsm_data.get("current_mapping_field")

    cm = ExternalConnectionManager()
    client_db = cm.get_db(uri, db_name)
    vals = await client_db[col_name].distinct(field_path)

    if len(vals) > 25:
        await ctx.state.merge_data(user_id, temp_enum_vals=[str(v) for v in vals[:25]])
        panel = tpl.render_enum_too_many_prompt(len(vals))
        await _edit_panel(client, user_id, message_id, panel)
        return

    vals = [str(v) for v in vals if v is not None]
    await ctx.state.merge_data(user_id, temp_enum_vals=vals)

    text, kb_spec = tpl.get_enum_order_prompt(vals)
    await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_enum_order", keyboard=_make_kb(kb_spec), edit_message_id=message_id)

async def _run_numeric_minmax_query(client: Client, message_id: int | None, ctx: HandlerContext, user_id: int):
    fsm_data = await ctx.state.data(user_id)
    uri = fsm_data.get("extdir_uri")
    db_name = fsm_data.get("extdir_db")
    col_name = fsm_data.get("extdir_col")
    field_path = fsm_data.get("current_mapping_field")

    cm = ExternalConnectionManager()
    client_db = cm.get_db(uri, db_name)

    pipeline = [
        {"$group": {"_id": None, "min": {"$min": f"${field_path}"}, "max": {"$max": f"${field_path}"}}}
    ]
    cursor = client_db[col_name].aggregate(pipeline)
    docs = await cursor.to_list(length=1)

    if docs:
        min_v = docs[0].get("min", 0)
        max_v = docs[0].get("max", 0)
    else:
        min_v = max_v = 0

    if not isinstance(min_v, (int, float)):
        min_v = 0
    if not isinstance(max_v, (int, float)):
        max_v = 0

    await ctx.state.merge_data(user_id, temp_num_min=float(min_v), temp_num_max=float(max_v))

    text, kb_spec = tpl.render_numeric_info_prompt(field_path, float(min_v), float(max_v))
    await akc.ask(client, ctx.db, chat_id=user_id, user_id=user_id, text=text, context="extdir_numeric_thresh", keyboard=_make_kb(kb_spec), edit_message_id=message_id)

# ---------------------------------------------------------------------------
# Handlers logic for ask and confirm inputs
# ---------------------------------------------------------------------------
async def _on_extdir_db(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    db_name = message.text.strip()

    # Delete message
    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    await ctx.state.merge_data(user_id, extdir_db=db_name)

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Captured DB.", clear_state=False)

    text, kb_spec = tpl.get_collection_prompt()
    await akc.ask(client, ctx.db, chat_id=message.chat.id, user_id=user_id, text=text, context="extdir_col", keyboard=_make_kb(kb_spec), edit_message_id=state_obj.prompt_msg_id if state_obj else None)

async def _on_extdir_col(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    col_name = message.text.strip()

    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    await ctx.state.merge_data(user_id, extdir_col=col_name)

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Captured Collection. Testing connection...", clear_state=False)

    await _run_test_connection(client, state_obj.prompt_msg_id if state_obj else None, ctx, user_id)

async def _on_extdir_custom_field(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    field_path = message.text.strip()
    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    fsm_data = await ctx.state.data(user_id)
    current_step = fsm_data.get("current_step")

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text=f"Captured custom field {field_path}.", clear_state=False)



    if current_step == "id":
        await ctx.state.merge_data(user_id, extdir_id_field=field_path, extdir_id_is_string=True)
        panel = tpl.render_expiry_prompt()
        await _edit_panel(client, user_id, state_obj.prompt_msg_id if state_obj else None, panel)
    elif current_step == "expiry":
        await ctx.state.merge_data(user_id, extdir_expiry_field=field_path)
        await _render_field_summary_step(client, state_obj.prompt_msg_id if state_obj else None, ctx, user_id)
    elif current_step == "mapping":
        await ctx.state.merge_data(user_id, current_mapping_field=field_path)
        panel = tpl.render_mapping_kind_prompt(field_path, "custom", "Unknown")
        await _edit_panel(client, user_id, state_obj.prompt_msg_id if state_obj else None, panel)

async def _on_extdir_enum_order(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    text = message.text.strip()
    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    vals = [v.strip() for v in text.replace("\n", ",").split(",") if v.strip()]

    await ctx.state.merge_data(user_id, temp_ordered_vals=vals)

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Captured ordered values.", clear_state=False)

    panel = tpl.render_enum_vip_prompt(vals)
    await _edit_panel(client, user_id, state_obj.prompt_msg_id if state_obj else None, panel)

async def _on_extdir_numeric_thresh(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    try:
        thresh = float(message.text.strip())
    except ValueError:
        state = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
        if state:
            await akc.fail(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state, error_text="Must be a valid number.\nTry again or /cancel.")
        return

    await ctx.state.merge_data(user_id, temp_num_thresh=thresh)

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Captured threshold.", clear_state=False)

    fsm_data = await ctx.state.data(user_id)
    min_val = fsm_data.get("temp_num_min", 0)
    max_val = fsm_data.get("temp_num_max", 0)

    if thresh < min_val or thresh > max_val:
        panel = tpl.render_numeric_warning_prompt(thresh, min_val, max_val)
        await _edit_panel(client, user_id, state_obj.prompt_msg_id if state_obj else None, panel)
    else:
        # Save directly
        field_path = fsm_data.get("current_mapping_field")
        mapping = {
            "local_name": "priority_score",
            "external_field_path": field_path,
            "kind": "numeric_threshold",
            "numeric_vip_threshold": thresh
        }

        mappings = list(fsm_data.get("extdir_mappings", []))
        mappings.append(mapping)
        await ctx.state.merge_data(user_id, extdir_mappings=mappings)
        await _render_field_summary_step(client, state_obj.prompt_msg_id if state_obj else None, ctx, user_id)

async def _on_extdir_test_id(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    try:
        tid = int(message.text.strip())
    except ValueError:
        state = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
        if state:
            await akc.fail(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state, error_text="Must be a valid integer ID.\nTry again or /cancel.")
        return

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Running lookup...", clear_state=True)

    from xtv_support.services.external_directory.factory import DirectoryProviderLike
    provider = ctx.container.resolve(DirectoryProviderLike)
    try:
        signal = await provider.get_signal(tid)
        res = (
            f"<b>Resolved Signal for {tid}:</b>\n"
            f"VIP: {signal.is_vip}\n"
            f"Tier: {signal.tier_label} (Rank: {signal.tier_rank_order})\n"
            f"Priority Score: {signal.priority_score}\n"
            f"Display Badge: {signal.display_badge}\n"
            f"Source: {signal.source}"
        )
    except Exception as e:
        res = f"Error performing lookup: {str(e)}"

    panel = tpl.render_test_result(user_id, res)
    await _edit_panel(client, user_id, state_obj.prompt_msg_id if state_obj else None, panel)

akc.register("extdir_db", _on_extdir_db)
akc.register("extdir_col", _on_extdir_col)
akc.register("extdir_custom_field", _on_extdir_custom_field)
akc.register("extdir_enum_order", _on_extdir_enum_order)
akc.register("extdir_numeric_thresh", _on_extdir_numeric_thresh)
akc.register("extdir_test_id", _on_extdir_test_id)


async def _on_extdir_uri(ctx: HandlerContext, client: Client, message: Message, args: dict[str, Any]) -> None:
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    uri = message.text.strip()
    if not uri.startswith("mongodb"):
        state = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
        if state:
            await akc.fail(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state, error_text="URI must start with mongodb:// or mongodb+srv://\nTry again or /cancel.")
        return

    # Delete message for security
    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except Exception:
        pass

    state_obj = akc.extract(await ctx.db.users.find_one({"user_id": user_id}, projection={"state": 1, "data": 1}))
    if state_obj:
        await akc.confirm(client, ctx.db, user_id=user_id, reply_chat_id=message.chat.id, reply_msg_id=message.id, state=state_obj, confirmation_text="Captured URI.", clear_state=False)

    # Store uri, go to step 2
    await ctx.state.merge_data(user_id, extdir_uri=uri)

    text, kb_spec = tpl.get_db_prompt(None)
    await akc.ask(client, ctx.db, chat_id=message.chat.id, user_id=user_id, text=text, context="extdir_db", keyboard=_make_kb(kb_spec), edit_message_id=state_obj.prompt_msg_id if state_obj else None)

akc.register("extdir_uri", _on_extdir_uri)
