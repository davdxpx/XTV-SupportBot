"""Macro topic commands.

Grammar (inside a forum-topic of the admin supergroup)::

    /macro list                — all macros visible to this topic's team
    /macro save <name>         — save the replied-to message as a macro
    /macro save <name> <body>  — inline form without reply
    /macro use <name>          — forward the expanded body to the user
    /macro show <name>         — preview without sending
    /macro del <name>          — delete a macro (owner/admin only)

The "team" a topic belongs to is derived from ``tickets.team_id``
(populated by the routing dispatcher). If no team is set, team-scope
operations fall back to global.
"""
from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.filters import is_admin_forum_topic
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import macros as macros_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.infrastructure.db.macros import InvalidMacroNameError
from xtv_support.services.macros.service import consume, render

log = get_logger("macro_cmd")

USAGE = (
    "<b>/macro</b>\n"
    "  /macro list\n"
    "  /macro save &lt;name&gt; (reply to a message) or /macro save &lt;name&gt; &lt;body&gt;\n"
    "  /macro use &lt;name&gt;\n"
    "  /macro show &lt;name&gt;\n"
    "  /macro del &lt;name&gt;"
)


def _args(message: Message) -> list[str]:
    parts = (message.text or "").strip().split(maxsplit=1)
    return parts[1].split(maxsplit=10) if len(parts) == 2 else []


async def _ticket_team_id(ctx, topic_id: int | None) -> tuple[str | None, str | None]:
    """Return ``(ticket_id, team_id)`` for the current topic (both may be None)."""
    if topic_id is None:
        return (None, None)
    doc = await ctx.db.tickets.find_one(
        {"topic_id": topic_id}, projection={"_id": 1, "team_id": 1}
    )
    if doc is None:
        return (None, None)
    return (str(doc["_id"]), doc.get("team_id"))


@Client.on_message(is_admin_forum_topic & filters.command("macro"), group=HandlerGroup.TOPIC)
async def macro_cmd(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        require(Role.AGENT)
    except AdminOnly:
        await message.reply_text("🚫 Agent role required.")
        return

    ctx = get_context(client)
    args = _args(message)
    if not args:
        await message.reply_text(USAGE)
        return

    sub, *rest = args
    sub = sub.lower()
    ticket_id, team_id = await _ticket_team_id(ctx, message.message_thread_id)

    try:
        if sub == "list":
            await _list(ctx, message, team_id)
        elif sub == "save":
            await _save(ctx, message, rest, team_id)
        elif sub in ("use", "send"):
            await _use(client, ctx, message, rest, team_id, ticket_id)
        elif sub == "show":
            await _show(ctx, message, rest, team_id)
        elif sub in ("del", "delete", "rm"):
            await _delete(ctx, message, rest, team_id)
        else:
            await message.reply_text(USAGE)
    except InvalidMacroNameError as exc:
        await message.reply_text(f"⚠️ {exc}")
    except Exception as exc:  # noqa: BLE001
        log.exception("macro_cmd.failed", sub=sub, error=str(exc))
        await message.reply_text(f"❌ Error: {exc}")


async def _list(ctx, message: Message, team_id: str | None) -> None:
    macros = await macros_repo.list_visible(ctx.db, team_id=team_id)
    if not macros:
        await message.reply_text("No macros visible in this scope yet.")
        return
    lines = [f"<b>Macros ({len(macros)})</b>"]
    for m in macros:
        preview = (m.body[:60] + "…") if len(m.body) > 60 else m.body
        lines.append(
            f"  • <code>{m.name}</code> ({m.scope}) · "
            f"used {m.usage_count}× — <i>{preview}</i>"
        )
    await message.reply_text("\n".join(lines))


async def _save(ctx, message: Message, rest: list[str], team_id: str | None) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/macro save &lt;name&gt; [body|reply]</code>")
        return
    name = rest[0]
    # Body candidates: (1) inline after name, (2) replied-to message text
    body: str | None = None
    if len(rest) >= 2:
        body = " ".join(rest[1:])
    elif message.reply_to_message and (
        message.reply_to_message.text or message.reply_to_message.caption
    ):
        body = message.reply_to_message.text or message.reply_to_message.caption

    if not body:
        await message.reply_text(
            "No body provided. Either inline <code>/macro save name body</code> "
            "or reply to a message with <code>/macro save name</code>."
        )
        return

    try:
        macro = await macros_repo.create(
            ctx.db,
            name=name,
            body=body,
            team_id=team_id,          # None -> global
            created_by=message.from_user.id,
        )
    except ValueError as exc:
        await message.reply_text(f"⚠️ {exc}")
        return

    log.info(
        "macro.saved",
        name=name,
        scope=macro.scope,
        by=message.from_user.id,
        len=len(body),
    )
    await message.reply_text(
        f"✅ Saved macro <code>{macro.name}</code> ({macro.scope})."
    )


async def _use(
    client: Client,
    ctx,
    message: Message,
    rest: list[str],
    team_id: str | None,
    ticket_id: str | None,
) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/macro use &lt;name&gt;</code>")
        return
    if ticket_id is None:
        await message.reply_text("Can't find a ticket for this topic.")
        return
    name = rest[0]
    macro = await macros_repo.get_by_name(ctx.db, name, team_id=team_id)
    if macro is None:
        await message.reply_text(f"No macro <code>{name}</code> visible here.")
        return

    # Resolve the ticket's user so macros can reference ``{user_name}``.
    ticket_doc = await tickets_repo.get(ctx.db, ticket_id)
    user_id = (ticket_doc or {}).get("user_id")
    if not user_id:
        await message.reply_text("No user on this ticket — nothing to send.")
        return

    user_first_name = ""
    try:
        user = await client.get_users(user_id)
        user_first_name = getattr(user, "first_name", "") or ""
    except Exception:  # noqa: BLE001 — proceed without name on Telegram hiccups
        pass

    rendered = render(
        macro,
        ticket_id=ticket_id,
        user_id=user_id,
        user_name=user_first_name,
    )
    try:
        await client.send_message(chat_id=user_id, text=rendered)
    except Exception as exc:  # noqa: BLE001
        log.warning("macro.send_failed", user_id=user_id, error=str(exc))
        await message.reply_text(f"⚠️ Send failed: {exc}")
        return

    await message.reply_text(
        f"✅ Sent macro <code>{macro.name}</code> to <code>{user_id}</code>."
    )
    await consume(
        ctx.db, ctx.bus,
        macro=macro, ticket_id=ticket_id, actor_id=message.from_user.id,
    )


async def _show(ctx, message: Message, rest: list[str], team_id: str | None) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/macro show &lt;name&gt;</code>")
        return
    name = rest[0]
    macro = await macros_repo.get_by_name(ctx.db, name, team_id=team_id)
    if macro is None:
        await message.reply_text(f"No macro <code>{name}</code> visible here.")
        return
    await message.reply_text(
        f"<b>{macro.name}</b> ({macro.scope}) · used {macro.usage_count}×\n\n"
        f"<blockquote expandable>{macro.body}</blockquote>"
    )


async def _delete(ctx, message: Message, rest: list[str], team_id: str | None) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/macro del &lt;name&gt;</code>")
        return
    name = rest[0]
    macro = await macros_repo.get_by_name(ctx.db, name, team_id=team_id)
    if macro is None:
        await message.reply_text(f"No macro <code>{name}</code> visible here.")
        return

    # Deleting a global macro is an admin-only action.
    if macro.team_id is None:
        try:
            require(Role.ADMIN)
        except AdminOnly:
            await message.reply_text("🚫 Only admins can delete global macros.")
            return

    removed = await macros_repo.delete(ctx.db, macro.id)
    if removed:
        log.info("macro.deleted", name=name, by=message.from_user.id)
        await message.reply_text(f"🗑️ Deleted <code>{name}</code>.")
    else:
        await message.reply_text("Delete failed.")


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
