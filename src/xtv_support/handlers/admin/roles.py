"""Role management commands — ``/role …``.

Only the **owner** can grant :attr:`Role.OWNER`. Admins can grant every
role up to and including :attr:`Role.ADMIN`.

Grammar
-------
``/role list``                — every role assignment in the system
``/role list <role>``         — only users of that role
``/role grant <uid> <role>``  — create or update an assignment
``/role revoke <uid>``        — delete an assignment (drops to user)
``/role me``                  — show the caller's own resolved role
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import current, require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import roles as roles_repo

log = get_logger("role_cmd")

USAGE = (
    "<b>Role commands</b>\n"
    "  /role list [role]\n"
    "  /role grant &lt;user_id&gt; &lt;role&gt;\n"
    "  /role revoke &lt;user_id&gt;\n"
    "  /role me\n"
    "\n"
    f"<i>Roles:</i> {', '.join(r.value for r in Role)}"
)


def _args(message: Message) -> list[str]:
    parts = (message.text or "").strip().split(maxsplit=1)
    return parts[1].split() if len(parts) == 2 else []


@Client.on_message(filters.private & filters.command("role"), group=HandlerGroup.COMMAND)
async def role_command(client: Client, message: Message) -> None:
    ctx = get_context(client)
    args = _args(message)

    # ``/role me`` is free for every authenticated user.
    if args and args[0].lower() == "me":
        await message.reply_text(f"Your resolved role: <b>{current().value}</b>")
        return

    # Everything else requires admin.
    try:
        require(Role.ADMIN)
    except AdminOnly:
        await message.reply_text("🚫 Admin role required.")
        return

    if not args:
        await message.reply_text(USAGE)
        return

    sub, *rest = args
    sub = sub.lower()
    try:
        if sub == "list":
            await _list_roles(ctx, message, rest)
        elif sub == "grant":
            await _grant_role(ctx, message, rest)
        elif sub == "revoke":
            await _revoke_role(ctx, message, rest)
        else:
            await message.reply_text(USAGE)
    except Exception as exc:  # noqa: BLE001
        log.exception("role_command.failed", sub=sub, error=str(exc))
        await message.reply_text(f"❌ Error: {exc}")


async def _list_roles(ctx, message: Message, rest: list[str]) -> None:
    if rest:
        try:
            role = Role(rest[0].lower())
        except ValueError:
            await message.reply_text(f"Unknown role: {rest[0]}")
            return
        assignments = await roles_repo.list_by_role(ctx.db, role)
        if not assignments:
            await message.reply_text(f"No users with role <b>{role.value}</b>.")
            return
        lines = [f"<b>Role: {role.value}</b>"]
        for a in assignments:
            teams = ",".join(a.team_ids) if a.team_ids else "—"
            lines.append(f"  • <code>{a.user_id}</code> — teams: {teams}")
        await message.reply_text("\n".join(lines))
        return

    # No filter — aggregate per role.
    from collections import defaultdict

    buckets: dict[Role, list[int]] = defaultdict(list)
    for role in Role:
        for a in await roles_repo.list_by_role(ctx.db, role):
            buckets[role].append(a.user_id)

    lines = ["<b>Role assignments</b>"]
    any_found = False
    for role in Role:
        if not buckets[role]:
            continue
        any_found = True
        ids = ", ".join(f"<code>{u}</code>" for u in sorted(buckets[role]))
        lines.append(f"  <b>{role.value}</b> ({len(buckets[role])}): {ids}")
    if not any_found:
        lines.append("  <i>no assignments — every user is the default USER role</i>")
    await message.reply_text("\n".join(lines))


async def _grant_role(ctx, message: Message, rest: list[str]) -> None:
    if len(rest) < 2:
        await message.reply_text(
            "Usage: <code>/role grant &lt;user_id&gt; &lt;role&gt; [team,…]</code>"
        )
        return
    try:
        uid = int(rest[0])
    except ValueError:
        await message.reply_text("user_id must be an integer.")
        return
    try:
        role = Role(rest[1].lower())
    except ValueError:
        await message.reply_text(f"Unknown role: {rest[1]}")
        return

    # Only an owner may grant OWNER.
    if role is Role.OWNER and not current().can(Role.OWNER):
        await message.reply_text("🚫 Only an owner can grant the <b>owner</b> role.")
        return

    team_ids: list[str] | None = None
    if len(rest) >= 3:
        team_ids = [t.strip() for t in rest[2].split(",") if t.strip()]

    await roles_repo.grant(
        ctx.db,
        user_id=uid,
        role=role,
        granted_by=message.from_user.id,
        team_ids=team_ids,
    )
    log.info(
        "role.granted",
        user_id=uid,
        role=role.value,
        by=message.from_user.id,
        teams=team_ids,
    )
    suffix = f" (teams: {','.join(team_ids)})" if team_ids else ""
    await message.reply_text(f"✅ Granted <b>{role.value}</b> to <code>{uid}</code>{suffix}.")


async def _revoke_role(ctx, message: Message, rest: list[str]) -> None:
    if not rest:
        await message.reply_text("Usage: <code>/role revoke &lt;user_id&gt;</code>")
        return
    try:
        uid = int(rest[0])
    except ValueError:
        await message.reply_text("user_id must be an integer.")
        return

    existing = await roles_repo.get_role(ctx.db, uid)
    if existing is None:
        await message.reply_text(f"<code>{uid}</code> has no explicit role.")
        return
    # Prevent non-owners from revoking an owner.
    if existing.role is Role.OWNER and not current().can(Role.OWNER):
        await message.reply_text("🚫 Only an owner can revoke an owner.")
        return

    await roles_repo.revoke(ctx.db, uid)
    log.info("role.revoked", user_id=uid, by=message.from_user.id)
    await message.reply_text(f"🗑️ Revoked role for <code>{uid}</code>.")


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
