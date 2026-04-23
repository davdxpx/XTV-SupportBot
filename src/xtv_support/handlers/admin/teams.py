"""Team management commands — ``/team …``.

Supervisor+ role is required. Commands operate on the ``teams``
collection introduced in Phase 5a and integrate with the routing
engine from Phase 5c.

Grammar
-------
``/team list``                    — show all teams with member counts
``/team create <slug> <name>``    — create a new team
``/team rename <slug> <new>``     — change the display name
``/team delete <slug>``           — remove a team
``/team tz <slug> <tz>``          — set IANA timezone (Europe/Berlin, UTC, …)
``/team members <slug>``          — list member ids
``/team addmember <slug> <id>``   — add a member
``/team removemember <slug> <id>``— remove a member
"""
from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import teams as teams_repo
from xtv_support.infrastructure.db.teams import InvalidSlugError

log = get_logger("team_cmd")

USAGE = (
    "<b>Team commands</b>\n"
    "  /team list\n"
    "  /team create &lt;slug&gt; &lt;name&gt;\n"
    "  /team rename &lt;slug&gt; &lt;new_name&gt;\n"
    "  /team delete &lt;slug&gt;\n"
    "  /team tz &lt;slug&gt; &lt;IANA_tz&gt;\n"
    "  /team members &lt;slug&gt;\n"
    "  /team addmember &lt;slug&gt; &lt;user_id&gt;\n"
    "  /team removemember &lt;slug&gt; &lt;user_id&gt;"
)


async def _ensure_sup(message: Message) -> bool:
    """Reply + return False if the caller is below SUPERVISOR."""
    try:
        require(Role.SUPERVISOR)
    except AdminOnly:
        await message.reply_text("🚫 Supervisor role required.")
        return False
    return True


def _args(message: Message) -> list[str]:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    return parts[1].split() if len(parts) == 2 else []


@Client.on_message(filters.private & filters.command("team"), group=HandlerGroup.COMMAND)
async def team_command(client: Client, message: Message) -> None:
    if not await _ensure_sup(message):
        return
    ctx = get_context(client)
    args = _args(message)
    if not args:
        await message.reply_text(USAGE)
        return

    sub, *rest = args
    sub = sub.lower()

    try:
        if sub == "list":
            await _list_teams(ctx, message)
        elif sub == "create":
            await _create_team(ctx, message, rest)
        elif sub == "rename":
            await _rename_team(ctx, message, rest)
        elif sub == "delete":
            await _delete_team(ctx, message, rest)
        elif sub == "tz":
            await _set_timezone(ctx, message, rest)
        elif sub == "members":
            await _list_members(ctx, message, rest)
        elif sub == "addmember":
            await _add_member(ctx, message, rest)
        elif sub == "removemember":
            await _remove_member(ctx, message, rest)
        else:
            await message.reply_text(USAGE)
    except InvalidSlugError as exc:
        await message.reply_text(f"⚠️ {exc}")
    except Exception as exc:  # noqa: BLE001
        log.exception("team_command.failed", sub=sub, error=str(exc))
        await message.reply_text(f"❌ Error: {exc}")


# ----------------------------------------------------------------------
# Subcommand implementations
# ----------------------------------------------------------------------
async def _list_teams(ctx, message: Message) -> None:
    teams = await teams_repo.list_all(ctx.db)
    if not teams:
        await message.reply_text("No teams configured yet. Use <code>/team create</code>.")
        return
    lines = ["<b>Teams</b>"]
    for t in teams:
        rules = len(t.queue_rules)
        lines.append(
            f"• <code>{t.id}</code> — {t.name} · "
            f"{len(t.member_ids)} member(s) · {rules} rule(s) · tz={t.timezone}"
        )
    await message.reply_text("\n".join(lines))


async def _create_team(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) < 2:
        await message.reply_text("Usage: <code>/team create &lt;slug&gt; &lt;name&gt;</code>")
        return
    slug = rest[0]
    name = " ".join(rest[1:])
    existing = await teams_repo.get(ctx.db, slug)
    if existing is not None:
        await message.reply_text(f"Team <code>{slug}</code> already exists.")
        return
    team = await teams_repo.create(
        ctx.db, team_id=slug, name=name, created_by=message.from_user.id
    )
    log.info("team.created", slug=slug, name=name, by=message.from_user.id)
    await message.reply_text(
        f"✅ Created team <code>{team.id}</code> — {team.name}."
    )


async def _rename_team(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) < 2:
        await message.reply_text("Usage: <code>/team rename &lt;slug&gt; &lt;new_name&gt;</code>")
        return
    slug, *name_parts = rest
    name = " ".join(name_parts)
    if await teams_repo.get(ctx.db, slug) is None:
        await message.reply_text(f"No team <code>{slug}</code>.")
        return
    await teams_repo.rename(ctx.db, slug, name)
    await message.reply_text(f"✅ Renamed to {name}.")


async def _delete_team(ctx, message: Message, rest: list[str]) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/team delete &lt;slug&gt;</code>")
        return
    slug = rest[0]
    deleted = await teams_repo.delete(ctx.db, slug)
    if deleted:
        await message.reply_text(f"🗑️ Deleted <code>{slug}</code>.")
        log.info("team.deleted", slug=slug, by=message.from_user.id)
    else:
        await message.reply_text(f"No team <code>{slug}</code>.")


async def _set_timezone(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) != 2:
        await message.reply_text("Usage: <code>/team tz &lt;slug&gt; &lt;IANA_tz&gt;</code>")
        return
    slug, tz = rest
    if await teams_repo.get(ctx.db, slug) is None:
        await message.reply_text(f"No team <code>{slug}</code>.")
        return
    await teams_repo.set_timezone(ctx.db, slug, tz)
    await message.reply_text(f"✅ Timezone of <code>{slug}</code> set to <code>{tz}</code>.")


async def _list_members(ctx, message: Message, rest: list[str]) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/team members &lt;slug&gt;</code>")
        return
    slug = rest[0]
    team = await teams_repo.get(ctx.db, slug)
    if team is None:
        await message.reply_text(f"No team <code>{slug}</code>.")
        return
    if not team.member_ids:
        await message.reply_text(f"<b>{team.name}</b> has no members yet.")
        return
    ids = "\n".join(f"  • <code>{m}</code>" for m in team.member_ids)
    await message.reply_text(f"<b>{team.name}</b> members:\n{ids}")


async def _add_member(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) != 2:
        await message.reply_text("Usage: <code>/team addmember &lt;slug&gt; &lt;user_id&gt;</code>")
        return
    slug, raw_id = rest
    try:
        uid = int(raw_id)
    except ValueError:
        await message.reply_text("user_id must be an integer.")
        return
    if await teams_repo.get(ctx.db, slug) is None:
        await message.reply_text(f"No team <code>{slug}</code>.")
        return
    await teams_repo.add_member(ctx.db, slug, uid)
    await message.reply_text(f"✅ Added <code>{uid}</code> to <code>{slug}</code>.")


async def _remove_member(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) != 2:
        await message.reply_text("Usage: <code>/team removemember &lt;slug&gt; &lt;user_id&gt;</code>")
        return
    slug, raw_id = rest
    try:
        uid = int(raw_id)
    except ValueError:
        await message.reply_text("user_id must be an integer.")
        return
    await teams_repo.remove_member(ctx.db, slug, uid)
    await message.reply_text(f"✅ Removed <code>{uid}</code> from <code>{slug}</code>.")

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
