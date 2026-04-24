"""API-key management — ``/apikey`` command + ``/admin`` API tab.

Fixes the missing-handler bug that swallowed ``/apikey create admin:full``
silently (the documentation promised the command, but no handler was
ever registered). Adds a button-driven menu so operators don't need to
remember the sub-command grammar.

Surface
-------
- **``/apikey``** in admin DM — opens the key-management card (gated
  on ``API_ENABLED=true``; if the API is off, the bot answers with a
  friendly hint instead of silence).
- **``/apikey create <scope[,scope…]> [label]``** — power-user shortcut.
  Plaintext key is shown **once**.
- **``/admin`` → Settings tab → 🔑 API keys** — opens the same card.

Menu flow
---------
The card lists every non-revoked key with a 🗑 revoke button. Tapping
`➕ Create key` drops into an AskAndConfirm prompt that asks for the
scopes (plus optional label), delete-edits the reply and shows the
plaintext key on the same card — exactly once.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from xtv_support.api import security as api_sec
from xtv_support.config.settings import settings
from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.ui.primitives import ask_and_confirm as akc

log = get_logger("admin.apikey_menu")

HR = "━" * 20
BACK_TO_SETTINGS = "cb:v2:admin:section:settings"


# ---------------------------------------------------------------------------
# Keyboards + rendering
# ---------------------------------------------------------------------------
def _kb_key_list(keys: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for k in keys:
        scope_preview = (
            ",".join(k.scopes[:2]) + ("…" if len(k.scopes) > 2 else "") if k.scopes else "—"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    f"🔑 {k.label or '(no label)'} · {scope_preview}",
                    callback_data=f"cb:v2:admin:apikey:view:{k.key_id}",
                ),
                InlineKeyboardButton(
                    "🗑",
                    callback_data=f"cb:v2:admin:apikey:revoke:{k.key_id}",
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton("➕ Create key", callback_data="cb:v2:admin:apikey:new"),
            InlineKeyboardButton("◀ Back", callback_data=BACK_TO_SETTINGS),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _kb_key_detail(key_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Revoke",
                    callback_data=f"cb:v2:admin:apikey:revoke:{key_id}",
                ),
                InlineKeyboardButton(
                    "◀ Back to list",
                    callback_data="cb:v2:admin:apikey:list",
                ),
            ]
        ]
    )


def _kb_revoke_confirm(key_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Yes, revoke",
                    callback_data=f"cb:v2:admin:apikey:revoke:{key_id}:confirm",
                ),
                InlineKeyboardButton(
                    "◀ Cancel",
                    callback_data="cb:v2:admin:apikey:list",
                ),
            ]
        ]
    )


def _scope_hint() -> str:
    return ", ".join(f"<code>{s}</code>" for s in api_sec.SCOPES)


def _api_disabled_text() -> str:
    return (
        f"<b>🔑 API keys</b>\n{HR}\n"
        "The REST API is currently <b>disabled</b>.\n\n"
        "<blockquote>⚙️ Set <code>API_ENABLED=true</code> in your environment "
        "and redeploy — then reopen this menu to mint keys.</blockquote>\n"
        f"{HR}"
    )


def _fmt_scopes(scopes: tuple[str, ...] | list[str]) -> str:
    return ", ".join(f"<code>{s}</code>" for s in scopes) if scopes else "<i>none</i>"


def _fmt_ts(ts) -> str:
    if ts is None:
        return "<i>never</i>"
    try:
        return ts.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:  # noqa: BLE001
        return str(ts)


# ---------------------------------------------------------------------------
# List / detail / create-confirm renderers
# ---------------------------------------------------------------------------
async def _render_list(client: Client, cq: CallbackQuery | None, message: Message | None) -> None:
    ctx = get_context(client)
    if not bool(getattr(settings, "API_ENABLED", False)):
        await _send_or_edit(client, cq, message, _api_disabled_text(), None)
        if cq is not None:
            await cq.answer()
        return
    keys = await api_sec.list_keys(ctx.db, include_revoked=False)
    header = f"<b>🔑 API keys</b>\n{HR}"
    if not keys:
        body = (
            f"{header}\n"
            "<i>No active keys.</i>\n\n"
            "<blockquote>➕ Tap <b>Create key</b> to mint one.</blockquote>\n"
            f"{HR}"
        )
    else:
        lines = [header, f"<i>{len(keys)} active</i>", ""]
        for k in keys:
            lines.append(
                f"• <b>{k.label or '(no label)'}</b>  "
                f"<i>id</i> <code>{k.key_id}</code>\n"
                f"  <i>scopes</i>: {_fmt_scopes(k.scopes)}\n"
                f"  <i>last used</i>: {_fmt_ts(k.last_used_at)}"
            )
        lines.append("")
        lines.append("<blockquote>🗑 Tap the trash next to a key to revoke it.</blockquote>")
        lines.append(HR)
        body = "\n".join(lines)
    await _send_or_edit(client, cq, message, body, _kb_key_list(keys))
    if cq is not None:
        await cq.answer()


async def _render_detail(client: Client, cq: CallbackQuery, key_id: str) -> None:
    ctx = get_context(client)
    # list_keys is the only read path today; look the key up by id.
    target = None
    for k in await api_sec.list_keys(ctx.db, include_revoked=True):
        if k.key_id == key_id:
            target = k
            break
    if target is None:
        await _send_or_edit(client, cq, None, "<i>Key not found.</i>", _kb_key_list([]))
        await cq.answer()
        return
    body = (
        f"<b>🔑 {target.label or '(no label)'}</b>\n"
        f"<i>id</i> <code>{target.key_id}</code>\n"
        f"<i>scopes</i>: {_fmt_scopes(target.scopes)}\n"
        f"<i>created</i>: {_fmt_ts(target.created_at)}\n"
        f"<i>last used</i>: {_fmt_ts(target.last_used_at)}\n"
        f"<i>revoked</i>: {_fmt_ts(target.revoked_at) if target.revoked_at else '—'}"
    )
    await _send_or_edit(client, cq, None, body, _kb_key_detail(key_id))
    await cq.answer()


async def _send_or_edit(
    client: Client,
    cq: CallbackQuery | None,
    message: Message | None,
    text: str,
    keyboard: InlineKeyboardMarkup | None,
) -> None:
    from pyrogram.errors import MessageNotModified

    if cq is not None and cq.message is not None:
        try:
            await cq.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except MessageNotModified:
            pass
        except Exception as exc:  # noqa: BLE001
            log.debug("apikey_menu.edit_failed", error=str(exc))
        return
    if message is not None:
        await client.send_message(
            message.chat.id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


# ---------------------------------------------------------------------------
# /apikey command (power-user backup)
# ---------------------------------------------------------------------------
@Client.on_message(
    filters.command("apikey") & is_admin_user & is_private,
    group=HandlerGroup.COMMAND,
)
async def apikey_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    text = (message.text or "").strip()
    parts = text.split(maxsplit=2)
    # /apikey                 → menu
    # /apikey create <scopes> [label]
    if len(parts) < 2:
        await _render_list(client, None, message)
        return

    sub = parts[1].lower()

    if sub == "list":
        await _render_list(client, None, message)
        return

    if sub == "create":
        if not bool(getattr(settings, "API_ENABLED", False)):
            await message.reply(_api_disabled_text())
            return
        rest = parts[2].split() if len(parts) == 3 else []
        if not rest:
            await message.reply(
                "Usage: <code>/apikey create &lt;scope[,scope…]&gt; [label]</code>\n"
                f"Available scopes: {_scope_hint()}"
            )
            return
        scopes_raw = rest[0]
        label = " ".join(rest[1:]) if len(rest) > 1 else "cli"
        scopes = [s for s in scopes_raw.split(",") if s]
        try:
            created = await api_sec.create_key(
                ctx.db,
                label=label,
                scopes=scopes,
                created_by=message.from_user.id if message.from_user else 0,
            )
        except ValueError as exc:
            await message.reply(f"⚠️ {exc}\n\nAvailable scopes: {_scope_hint()}")
            return
        await message.reply(
            _fmt_new_key_card(created),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    if sub == "revoke":
        if len(parts) < 3:
            await message.reply("Usage: <code>/apikey revoke &lt;key_id&gt;</code>")
            return
        ok = await api_sec.revoke_key(ctx.db, parts[2].strip())
        await message.reply("🗑 Revoked." if ok else "Key not found.")
        return

    await message.reply(
        "Usage:\n"
        "  <code>/apikey</code>  — open the management menu\n"
        "  <code>/apikey create &lt;scopes&gt; [label]</code>\n"
        "  <code>/apikey revoke &lt;key_id&gt;</code>\n"
        "  <code>/apikey list</code>"
    )


def _fmt_new_key_card(created: api_sec.NewApiKey) -> str:
    return (
        f"<b>🔑 API key created</b>\n{HR}\n"
        f"<i>label</i>: <b>{created.meta.label}</b>\n"
        f"<i>scopes</i>: {_fmt_scopes(created.meta.scopes)}\n"
        f"<i>id</i>: <code>{created.meta.key_id}</code>\n\n"
        "<blockquote>⚠️ Save this now — it won't be shown again:</blockquote>\n"
        f"<code>{created.plaintext}</code>\n\n"
        "<blockquote>🔗 Use <code>Authorization: Bearer &lt;key&gt;</code> in requests.</blockquote>\n"
        f"{HR}"
    )


# ---------------------------------------------------------------------------
# Callback dispatcher
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^cb:v2:admin:apikey:"), group=HandlerGroup.COMMAND)
async def apikey_menu_callback(client: Client, cq: CallbackQuery) -> None:
    parts = (cq.data or "").split(":")
    action = parts[4] if len(parts) >= 5 else ""

    if action == "list":
        await _render_list(client, cq, None)
        return

    if action == "view":
        key_id = parts[5] if len(parts) >= 6 else ""
        await _render_detail(client, cq, key_id)
        return

    if action == "new":
        if not bool(getattr(settings, "API_ENABLED", False)):
            await cq.answer("API is disabled — set API_ENABLED=true.", show_alert=True)
            return
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                "<b>➕ New API key</b>\n\n"
                "Send the scopes the key should carry, optionally followed "
                "by a label.\n\n"
                "Format:  <code>&lt;scope[,scope…]&gt; [label]</code>\n"
                "Example: <code>tickets:read,analytics:read reporting</code>\n\n"
                f"Available scopes:\n{_scope_hint()}\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
            context="apikey:new",
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    if action == "revoke":
        key_id = parts[5] if len(parts) >= 6 else ""
        confirm = parts[6] if len(parts) >= 7 else ""
        if confirm == "confirm":
            ctx = get_context(client)
            ok = await api_sec.revoke_key(ctx.db, key_id)
            await cq.answer("Revoked." if ok else "Not found.", show_alert=False)
            await _render_list(client, cq, None)
            return
        # Show confirmation card
        await cq.message.edit_text(
            (
                f"<b>🗑 Revoke key?</b>\n{HR}\n"
                f"Key id <code>{key_id}</code> will be invalidated "
                "immediately. Any client using it will start getting "
                "401 <code>invalid_key</code> on the next request.\n\n"
                "<blockquote>⚠️ This cannot be undone.</blockquote>\n"
                f"{HR}"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_kb_revoke_confirm(key_id),
            disable_web_page_preview=True,
        )
        await cq.answer()
        return

    await cq.answer()


# ---------------------------------------------------------------------------
# AskAndConfirm handler — key creation
# ---------------------------------------------------------------------------
async def _on_apikey_new(ctx, client: Client, message: Message, args: dict) -> None:
    state = akc.extract(await users_repo.get(ctx.db, message.from_user.id))
    if state is None:
        return
    raw = (message.text or "").strip().split()
    if not raw:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                "<b>⚠️ Need at least a scope</b>\n\n"
                "Format: <code>&lt;scope[,scope…]&gt; [label]</code>\n"
                f"Scopes: {_scope_hint()}\n\n"
                "Send again, or <code>/cancel</code>."
            ),
        )
        return
    scopes_raw = raw[0]
    label = " ".join(raw[1:]) if len(raw) > 1 else "menu"
    scopes = [s for s in scopes_raw.split(",") if s]
    try:
        created = await api_sec.create_key(
            ctx.db,
            label=label,
            scopes=scopes,
            created_by=message.from_user.id,
        )
    except ValueError as exc:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(f"<b>⚠️ {exc}</b>\n\nAvailable scopes:\n{_scope_hint()}"),
        )
        return
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=_fmt_new_key_card(created),
        keyboard=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "◀ Back to keys",
                        callback_data="cb:v2:admin:apikey:list",
                    )
                ]
            ]
        ),
    )


akc.register("apikey:new", _on_apikey_new)
