"""Rule admin commands — minimal CRUD + toggle + dry-run.

Full graphical rule builder is Phase-4.6+ follow-up; for v1.0 we give
operators a small CLI surface that covers every operation the builder
will wrap.

Commands
--------
/rules                              list all rules (short form)
/rule_new "<name>" <trigger> JSON
    name (string, quoted), trigger (event class), JSON body:
      {"conditions":[...],"actions":[...], "cooldown_s": 0}
/rule_enable <id>
/rule_disable <id>
/rule_delete  <id>
/rule_test    <id> <ticket_id>      dry-run — evaluate conditions only
"""

from __future__ import annotations

import json
import shlex

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.services.rules.dry_run import dry_run as rules_dry_run
from xtv_support.services.rules.repository import (
    create_rule,
    delete_rule,
    enable_rule,
    get_rule,
    list_rules,
)

log = get_logger("admin.rules")


def _fmt_rule(rule) -> str:
    state = "✅" if rule.enabled else "⬜"
    conds = ", ".join(f"{c.field} {c.op} {c.value!r}" for c in rule.conditions) or "—"
    actions = ", ".join(a.name for a in rule.actions) or "—"
    return (
        f"{state}  <code>{rule.id}</code>  <b>{rule.name}</b>\n"
        f"<i>trigger</i>: {rule.trigger}  ·  <i>cooldown</i>: {rule.cooldown_s}s\n"
        f"<i>if</i>: {conds}\n"
        f"<i>then</i>: {actions}"
    )


@Client.on_message(
    filters.command("rules") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def rules_list(client: Client, message: Message) -> None:
    ctx = get_context(client)
    rules = await list_rules(ctx.db, limit=50)
    if not rules:
        await message.reply("<i>No automation rules yet.</i>\nCreate one with <code>/rule_new</code>.")
        return
    body = "\n\n".join(_fmt_rule(r) for r in rules)
    await message.reply(f"<b>Automation rules</b>\n\n{body}", disable_web_page_preview=True)


@Client.on_message(
    filters.command("rule_new") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def rule_new(client: Client, message: Message) -> None:
    ctx = get_context(client)
    text = message.text or ""
    # Expect: /rule_new "name" trigger {json}
    try:
        _cmd, name, trigger, *rest = shlex.split(text)
    except ValueError as exc:
        await message.reply(f"Parse error: {exc}")
        return
    if not rest:
        await message.reply(
            "Usage: <code>/rule_new \"name\" TicketCreated "
            '{"conditions":[{"field":"priority","op":"eq","value":"high"}],'
            '"actions":[{"name":"assign","params":{"assignee_id":123}}]}</code>'
        )
        return
    body_json = " ".join(rest)
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError as exc:
        await message.reply(f"Bad JSON: {exc}")
        return

    rule = await create_rule(
        ctx.db,
        name=name,
        trigger=trigger,
        conditions=body.get("conditions") or [],
        actions=body.get("actions") or [],
        cooldown_s=int(body.get("cooldown_s", 0) or 0),
        created_by=message.from_user.id if message.from_user else None,
        enabled=False,
    )
    await message.reply(
        f"✅ Rule created (disabled):\n{_fmt_rule(rule)}\n\n"
        f"Enable with <code>/rule_enable {rule.id}</code>"
    )


@Client.on_message(
    filters.command(["rule_enable", "rule_disable"]) & is_admin_user & is_private,
    group=HandlerGroup.COMMAND,
)
async def rule_toggle(client: Client, message: Message) -> None:
    ctx = get_context(client)
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("Usage: <code>/rule_enable &lt;id&gt;</code> or <code>/rule_disable &lt;id&gt;</code>")
        return
    cmd = parts[0].lstrip("/").split("@")[0]
    rule_id = parts[1]
    wanted = cmd == "rule_enable"
    ok = await enable_rule(ctx.db, rule_id, wanted)
    if not ok:
        await message.reply("Rule not found.")
        return
    await message.reply(f"{'✅ Enabled' if wanted else '⏸ Disabled'}: <code>{rule_id}</code>")


@Client.on_message(
    filters.command("rule_delete") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def rule_delete(client: Client, message: Message) -> None:
    ctx = get_context(client)
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("Usage: <code>/rule_delete &lt;id&gt;</code>")
        return
    ok = await delete_rule(ctx.db, parts[1])
    await message.reply("🗑 Deleted." if ok else "Rule not found.")


@Client.on_message(
    filters.command("rule_test") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def rule_test(client: Client, message: Message) -> None:
    ctx = get_context(client)
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.reply("Usage: <code>/rule_test &lt;rule_id&gt; &lt;ticket_id&gt;</code>")
        return
    rule = await get_rule(ctx.db, parts[1])
    if rule is None:
        await message.reply("Rule not found.")
        return
    from xtv_support.infrastructure.db import tickets as tickets_repo

    ticket = await tickets_repo.get(ctx.db, parts[2])
    if ticket is None:
        await message.reply("Ticket not found.")
        return
    result = rules_dry_run(rule, ticket)
    verdict = "✅ WOULD FIRE" if result.would_fire else "⬜ would NOT fire"
    lines = [f"<b>Dry-run</b>: {verdict}"]
    for c in result.conditions:
        icon = "✅" if c.matched else "❌"
        lines.append(f"  {icon} {c.field} {c.op} {c.value!r}")
    await message.reply("\n".join(lines))
