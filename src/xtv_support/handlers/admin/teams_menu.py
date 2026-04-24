"""Team management inline menu — ``/admin`` → Teams tab.

Complete button-driven flow for the ``teams`` subsystem. The old
``/team …`` command handler in :mod:`xtv_support.handlers.admin.teams`
stays untouched as a power-user backup; this module gives every admin
the same functionality without remembering sub-command grammar.

Callback scheme::

    cb:v2:admin:teams:list
    cb:v2:admin:teams:new
    cb:v2:admin:teams:view:<slug>
    cb:v2:admin:teams:rename:<slug>
    cb:v2:admin:teams:tz:<slug>
    cb:v2:admin:teams:delete:<slug>
    cb:v2:admin:teams:delete:<slug>:confirm
    cb:v2:admin:teams:members:<slug>
    cb:v2:admin:teams:members:add:<slug>
    cb:v2:admin:teams:members:remove:<slug>:<user_id>

All value-entry prompts (create/rename/tz/add member) route through
:mod:`xtv_support.ui.primitives.ask_and_confirm` so the admin's DM
stays clean: prompt → value → prompt edited to confirmation.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import teams as teams_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.infrastructure.db.teams import InvalidSlugError
from xtv_support.ui.primitives import ask_and_confirm as akc

log = get_logger("admin.teams_menu")

BACK_TO_TEAMS = "cb:v2:admin:tab:teams"


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------
def _kb_team_list(teams: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for t in teams:
        pair.append(
            InlineKeyboardButton(
                f"👥 {t.name}",
                callback_data=f"cb:v2:admin:teams:view:{t.id}",
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(
        [
            InlineKeyboardButton("➕ New team", callback_data="cb:v2:admin:teams:new"),
            InlineKeyboardButton("◀ Back", callback_data=BACK_TO_TEAMS),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _kb_team_detail(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Rename", callback_data=f"cb:v2:admin:teams:rename:{slug}"),
                InlineKeyboardButton("🌐 Timezone", callback_data=f"cb:v2:admin:teams:tz:{slug}"),
            ],
            [
                InlineKeyboardButton(
                    "👤 Members", callback_data=f"cb:v2:admin:teams:members:{slug}"
                ),
                InlineKeyboardButton("🗑 Delete", callback_data=f"cb:v2:admin:teams:delete:{slug}"),
            ],
            [
                InlineKeyboardButton("◀ Back to list", callback_data="cb:v2:admin:teams:list"),
            ],
        ]
    )


def _kb_members(slug: str, member_ids: list[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for uid in member_ids:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{uid}",
                    callback_data=f"cb:v2:admin:teams:members:noop:{slug}",
                ),
                InlineKeyboardButton(
                    "🗑",
                    callback_data=f"cb:v2:admin:teams:members:remove:{slug}:{uid}",
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                "➕ Add member",
                callback_data=f"cb:v2:admin:teams:members:add:{slug}",
            ),
            InlineKeyboardButton(
                "◀ Back",
                callback_data=f"cb:v2:admin:teams:view:{slug}",
            ),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _kb_delete_confirm(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Yes, delete",
                    callback_data=f"cb:v2:admin:teams:delete:{slug}:confirm",
                ),
                InlineKeyboardButton(
                    "◀ Cancel",
                    callback_data=f"cb:v2:admin:teams:view:{slug}",
                ),
            ]
        ]
    )


# ---------------------------------------------------------------------------
# Render helpers (edit the existing panel message)
# ---------------------------------------------------------------------------
async def _edit(cq: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup | None) -> None:
    from pyrogram.errors import MessageNotModified

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
        log.debug("teams_menu.edit_failed", error=str(exc))


async def _render_team_list(client: Client, cq: CallbackQuery) -> None:
    ctx = get_context(client)
    teams = await teams_repo.list_all(ctx.db)
    if not teams:
        body = (
            "<b>👥 Teams</b>\n\n"
            "<i>No teams configured yet.</i>\n"
            "Tap <b>➕ New team</b> to create one."
        )
    else:
        lines = ["<b>👥 Teams</b>", ""]
        for t in teams:
            lines.append(
                f"• <code>{t.id}</code> — {t.name}  "
                f"<i>({len(t.member_ids)} member(s), tz {t.timezone})</i>"
            )
        body = "\n".join(lines)
    await _edit(cq, body, _kb_team_list(teams))
    await cq.answer()


async def _render_team_detail(client: Client, cq: CallbackQuery, slug: str) -> None:
    ctx = get_context(client)
    team = await teams_repo.get(ctx.db, slug)
    if team is None:
        await _edit(
            cq,
            f"<b>👥 Teams</b>\n\n<i>Team <code>{slug}</code> not found.</i>",
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀ Back", callback_data="cb:v2:admin:teams:list")]]
            ),
        )
        await cq.answer()
        return
    text = (
        f"<b>👥 {team.name}</b>\n"
        f"<i>slug</i> <code>{team.id}</code>\n"
        f"<i>timezone</i> <code>{team.timezone}</code>\n"
        f"<i>members</i> {len(team.member_ids)}\n"
        f"<i>queue rules</i> {len(team.queue_rules)}"
    )
    await _edit(cq, text, _kb_team_detail(slug))
    await cq.answer()


async def _render_members(client: Client, cq: CallbackQuery, slug: str) -> None:
    ctx = get_context(client)
    team = await teams_repo.get(ctx.db, slug)
    if team is None:
        await cq.answer("Team not found.", show_alert=True)
        return
    if not team.member_ids:
        body = f"<b>👤 {team.name} — members</b>\n\n<i>No members yet.</i>"
    else:
        body = f"<b>👤 {team.name} — members</b>\n\n"
        body += "\n".join(f"• <code>{m}</code>" for m in team.member_ids)
    await _edit(cq, body, _kb_members(slug, list(team.member_ids)))
    await cq.answer()


async def _render_delete_confirm(client: Client, cq: CallbackQuery, slug: str) -> None:
    ctx = get_context(client)
    team = await teams_repo.get(ctx.db, slug)
    if team is None:
        await cq.answer("Team not found.", show_alert=True)
        return
    body = (
        f"<b>🗑 Delete team?</b>\n\n"
        f"This will permanently delete <b>{team.name}</b> "
        f"(<code>{team.id}</code>) and its {len(team.queue_rules)} routing rule(s).\n\n"
        f"Members ({len(team.member_ids)}) keep their user accounts."
    )
    await _edit(cq, body, _kb_delete_confirm(slug))
    await cq.answer()


# ---------------------------------------------------------------------------
# Callback dispatcher
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^cb:v2:admin:teams:"), group=HandlerGroup.COMMAND)
async def teams_menu_callback(client: Client, cq: CallbackQuery) -> None:
    parts = (cq.data or "").split(":")
    # cb:v2:admin:teams:<action>[:<arg>…]
    action = parts[4] if len(parts) >= 5 else ""

    if action == "list":
        await _render_team_list(client, cq)
        return

    if action == "new":
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                "<b>➕ New team</b>\n\n"
                "Send the new team's <b>slug</b> (short identifier, "
                "letters / digits / <code>-</code> / <code>_</code>) and "
                "<b>display name</b>, separated by a space.\n\n"
                "Example:  <code>billing Billing Support</code>\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
            context="teams:new",
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    if action == "view":
        slug = parts[5] if len(parts) >= 6 else ""
        await _render_team_detail(client, cq, slug)
        return

    if action == "rename":
        slug = parts[5] if len(parts) >= 6 else ""
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                f"<b>✏️ Rename team</b>  <code>{slug}</code>\n\n"
                f"Send the new display name.\n\n"
                f"<i>Send /cancel to abort.</i>"
            ),
            context="teams:rename",
            args={"slug": slug},
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    if action == "tz":
        slug = parts[5] if len(parts) >= 6 else ""
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                f"<b>🌐 Timezone</b>  <code>{slug}</code>\n\n"
                f"Send an IANA timezone identifier "
                f"(e.g. <code>Europe/Berlin</code>, <code>UTC</code>, "
                f"<code>America/New_York</code>).\n\n"
                f"<i>Send /cancel to abort.</i>"
            ),
            context="teams:tz",
            args={"slug": slug},
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    if action == "members":
        sub = parts[5] if len(parts) >= 6 else ""
        if sub == "add":
            slug = parts[6] if len(parts) >= 7 else ""
            ctx = get_context(client)
            await akc.ask(
                client,
                ctx.db,
                chat_id=cq.message.chat.id,
                user_id=cq.from_user.id,
                text=(
                    f"<b>➕ Add member to</b>  <code>{slug}</code>\n\n"
                    f"Send the Telegram user-id (a number) to add.\n\n"
                    f"<i>Send /cancel to abort.</i>"
                ),
                context="teams:member_add",
                args={"slug": slug},
                edit_message_id=cq.message.id,
            )
            await cq.answer()
            return
        if sub == "remove":
            slug = parts[6] if len(parts) >= 7 else ""
            uid_raw = parts[7] if len(parts) >= 8 else ""
            ctx = get_context(client)
            try:
                uid = int(uid_raw)
            except ValueError:
                await cq.answer("Bad user id.", show_alert=True)
                return
            await teams_repo.remove_member(ctx.db, slug, uid)
            await cq.answer(f"Removed {uid}.", show_alert=False)
            await _render_members(client, cq, slug)
            return
        if sub == "noop":
            await cq.answer()
            return
        # No sub → members list for the team.
        slug = sub
        await _render_members(client, cq, slug)
        return

    if action == "delete":
        slug = parts[5] if len(parts) >= 6 else ""
        confirm = parts[6] if len(parts) >= 7 else ""
        if confirm == "confirm":
            ctx = get_context(client)
            deleted = await teams_repo.delete(ctx.db, slug)
            if deleted:
                log.info(
                    "team.deleted",
                    slug=slug,
                    by=cq.from_user.id if cq.from_user else None,
                )
                await cq.answer("Deleted.", show_alert=False)
            else:
                await cq.answer("Team not found.", show_alert=True)
            await _render_team_list(client, cq)
            return
        await _render_delete_confirm(client, cq, slug)
        return

    await cq.answer()


# ---------------------------------------------------------------------------
# AskAndConfirm context handlers  (new signature: ctx, client, message, args)
# ---------------------------------------------------------------------------
async def _state_for(ctx, user_id: int) -> akc.AkcState | None:
    return akc.extract(await users_repo.get(ctx.db, user_id))


async def _on_team_new(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                "<b>⚠️ Need two tokens</b>\n\n"
                "Format: <code>&lt;slug&gt; &lt;name…&gt;</code>\n"
                "Example: <code>billing Billing Support</code>\n\n"
                "Send again, or <code>/cancel</code> to abort."
            ),
        )
        return
    slug, name = parts[0], parts[1]
    try:
        existing = await teams_repo.get(ctx.db, slug)
        if existing is not None:
            await akc.fail(
                client,
                ctx.db,
                user_id=message.from_user.id,
                reply_chat_id=message.chat.id,
                reply_msg_id=message.id,
                state=state,
                error_text=(
                    f"<b>⚠️ Slug taken</b>\n\n"
                    f"A team with slug <code>{slug}</code> already exists. "
                    f"Pick a different slug, or <code>/cancel</code>."
                ),
            )
            return
        team = await teams_repo.create(
            ctx.db, team_id=slug, name=name, created_by=message.from_user.id
        )
    except InvalidSlugError as exc:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(f"<b>⚠️ Invalid slug</b>\n\n{exc}\n\nTry again, or <code>/cancel</code>."),
        )
        return
    log.info("team.created", slug=slug, name=name, by=message.from_user.id)
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(f"<b>✅ Team created</b>\n\n<code>{team.id}</code> — {team.name}"),
        keyboard=_kb_team_detail(team.id),
    )


async def _on_team_rename(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    slug = str(args.get("slug") or "")
    new_name = (message.text or "").strip()
    if not new_name:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text="<b>⚠️ Name can't be empty</b>\n\nSend again, or <code>/cancel</code>.",
        )
        return
    if await teams_repo.get(ctx.db, slug) is None:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=f"<b>⚠️ Team <code>{slug}</code> no longer exists.</b>",
        )
        return
    await teams_repo.rename(ctx.db, slug, new_name)
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(f"<b>✅ Renamed</b>\n\n<code>{slug}</code> → {new_name}"),
        keyboard=_kb_team_detail(slug),
    )


async def _on_team_tz(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    slug = str(args.get("slug") or "")
    tz = (message.text or "").strip()
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(tz)
    except Exception as exc:  # noqa: BLE001
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Unknown timezone</b> <code>{tz}</code>\n\n{exc}\n\n"
                f"Use an IANA id like <code>Europe/Berlin</code>."
            ),
        )
        return
    if await teams_repo.get(ctx.db, slug) is None:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=f"<b>⚠️ Team <code>{slug}</code> no longer exists.</b>",
        )
        return
    await teams_repo.set_timezone(ctx.db, slug, tz)
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(
            f"<b>✅ Timezone updated</b>\n\n<code>{slug}</code> → <code>{tz}</code>"
        ),
        keyboard=_kb_team_detail(slug),
    )


async def _on_team_member_add(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    slug = str(args.get("slug") or "")
    raw = (message.text or "").strip()
    try:
        uid = int(raw)
    except ValueError:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                "<b>⚠️ Not a number</b>\n\n"
                "Send the user's numeric Telegram id.\n"
                "(Forward a message from them to @userinfobot to find it.)\n\n"
                "Try again, or <code>/cancel</code>."
            ),
        )
        return
    if await teams_repo.get(ctx.db, slug) is None:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=f"<b>⚠️ Team <code>{slug}</code> no longer exists.</b>",
        )
        return
    await teams_repo.add_member(ctx.db, slug, uid)
    team = await teams_repo.get(ctx.db, slug)
    member_ids = list(team.member_ids) if team else [uid]
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(
            f"<b>✅ Added</b>\n\n<code>{uid}</code> → <code>{slug}</code>\n"
            f"<i>{len(member_ids)} member(s) total</i>"
        ),
        keyboard=_kb_members(slug, member_ids),
    )


# ---------------------------------------------------------------------------
# Register AKC handlers at import time
# ---------------------------------------------------------------------------
akc.register("teams:new", _on_team_new)
akc.register("teams:rename", _on_team_rename)
akc.register("teams:tz", _on_team_tz)
akc.register("teams:member_add", _on_team_member_add)
