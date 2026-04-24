"""Project management inline menu — ``/admin → 📁 Projects``.

Wires the three buttons that landed dead after the drill-down rewrite:

- ``cb:v2:admin:projects:list`` → browse active projects
- ``cb:v2:admin:projects:from_template`` → template picker → create from one
- ``cb:v2:admin:projects:blank`` → AskAndConfirm flow for a blank project

The actual persistence goes through ``projects_repo`` (blank) or
``services.templates.install_template`` (from template). The legacy
``/project_template`` command stays as a power-user shortcut.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.services.templates import default_registry, install_template
from xtv_support.ui.primitives import ask_and_confirm as akc

log = get_logger("admin.projects_menu")

HR = "━" * 20
BACK_TO_PROJECTS = "cb:v2:admin:section:projects"


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------
def _kb_project_list(projects: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for p in projects:
        label = str(p.get("name") or p.get("slug") or "Project")
        pair.append(
            InlineKeyboardButton(
                f"📂 {label}",
                callback_data=f"cb:v2:admin:projects:view:{p.get('slug') or p.get('_id')}",
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(
        [
            InlineKeyboardButton(
                "🎯 From template", callback_data="cb:v2:admin:projects:from_template"
            ),
            InlineKeyboardButton("📄 Blank", callback_data="cb:v2:admin:projects:blank"),
        ]
    )
    rows.append([InlineKeyboardButton("◀ Back", callback_data=BACK_TO_PROJECTS)])
    return InlineKeyboardMarkup(rows)


def _kb_template_picker() -> InlineKeyboardMarkup:
    """2-per-row grid of the built-in ProjectTemplates."""
    templates = list(default_registry.list())
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for t in templates:
        pair.append(
            InlineKeyboardButton(
                f"{t.icon} {t.name}",
                callback_data=f"cb:v2:admin:projects:tpl_pick:{t.slug}",
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton("◀ Back", callback_data=BACK_TO_PROJECTS)])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Rendering helpers
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
        log.debug("projects_menu.edit_failed", error=str(exc))


async def _render_list(client: Client, cq: CallbackQuery) -> None:
    ctx = get_context(client)
    projects = await projects_repo.list_active(ctx.db)
    header = f"<b>📁 Projects</b>\n{HR}"
    if not projects:
        body = (
            f"{header}\n"
            "<i>No active projects yet.</i>\n\n"
            "<blockquote>🎯 Tap <b>From template</b> to seed one with macros / KB / "
            "routing in seconds, or <b>Blank</b> for a minimal project.</blockquote>\n"
            f"{HR}"
        )
    else:
        lines = [header, f"<i>{len(projects)} active</i>", ""]
        for p in projects:
            slug = p.get("slug") or "—"
            name = p.get("name") or slug
            tpl = p.get("template_slug") or "—"
            ticket_count = p.get("ticket_count", 0)
            lines.append(
                f"• <b>{name}</b>  <code>{slug}</code>\n"
                f"  <i>template</i>: {tpl}  ·  <i>tickets</i>: {ticket_count}"
            )
        lines.append("")
        lines.append(
            "<blockquote>➕ Tap <b>From template</b> or <b>Blank</b> below to add one.</blockquote>"
        )
        lines.append(HR)
        body = "\n".join(lines)
    await _edit(cq, body, _kb_project_list(projects))
    await cq.answer()


async def _render_template_picker(client: Client, cq: CallbackQuery) -> None:
    templates = list(default_registry.list())
    lines = [f"<b>🎯 Pick a template</b>\n{HR}"]
    for t in templates:
        lines.append(f"• {t.icon} <b>{t.name}</b>  <code>{t.slug}</code>")
        lines.append(f"  <i>{t.description}</i>")
    lines.append("")
    lines.append(
        "<blockquote>📘 Each template seeds macros, KB articles and routing "
        "rules so the new project is useful in seconds.</blockquote>"
    )
    lines.append(HR)
    await _edit(cq, "\n".join(lines), _kb_template_picker())
    await cq.answer()


async def _render_project_detail(client: Client, cq: CallbackQuery, slug: str) -> None:
    ctx = get_context(client)
    project = await ctx.db.projects.find_one({"slug": slug})
    if project is None:
        # Fall back to ObjectId lookup in case a legacy project has no slug.
        project = await projects_repo.get(ctx.db, slug)
    if project is None:
        await _edit(
            cq,
            f"<b>📁 Projects</b>\n{HR}\n<i>Project <code>{slug}</code> not found.</i>\n{HR}",
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀ Back", callback_data="cb:v2:admin:projects:list")]]
            ),
        )
        await cq.answer()
        return
    name = str(project.get("name") or slug)
    tpl = project.get("template_slug") or "—"
    desc = project.get("description") or "<i>no description</i>"
    body = (
        f"<b>📂 {name}</b>\n"
        f"{HR}\n"
        f"<i>slug</i> <code>{project.get('slug')}</code>\n"
        f"<i>template</i> <code>{tpl}</code>\n"
        f"<i>active</i> {'✅' if project.get('active') else '⬜'}\n"
        f"<i>ticket count</i> {project.get('ticket_count', 0)}\n\n"
        f"{desc}\n\n"
        "<blockquote>🗑 Delete lives on the legacy dashboard for now; the "
        "inline Delete button lands in a follow-up.</blockquote>\n"
        f"{HR}"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀ Back to list", callback_data="cb:v2:admin:projects:list")]]
    )
    await _edit(cq, body, kb)
    await cq.answer()


# ---------------------------------------------------------------------------
# Callback dispatcher
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^cb:v2:admin:projects:"), group=HandlerGroup.COMMAND)
async def projects_menu_callback(client: Client, cq: CallbackQuery) -> None:
    parts = (cq.data or "").split(":")
    # cb:v2:admin:projects:<action>[:<arg>…]
    action = parts[4] if len(parts) >= 5 else ""

    if action == "list":
        await _render_list(client, cq)
        return

    if action == "view":
        slug = parts[5] if len(parts) >= 6 else ""
        await _render_project_detail(client, cq, slug)
        return

    if action == "from_template":
        await _render_template_picker(client, cq)
        return

    if action == "tpl_pick":
        template_slug = parts[5] if len(parts) >= 6 else ""
        template = default_registry.get(template_slug)
        if template is None:
            await cq.answer("Unknown template.", show_alert=True)
            return
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                f"<b>🎯 New project from {template.icon} {template.name}</b>\n"
                f"{HR}\n"
                f"<i>{template.description}</i>\n\n"
                "Send the new project's <b>slug</b> (short identifier, "
                "letters / digits / <code>-</code> / <code>_</code>) and optional "
                "<b>display name</b>, separated by a space.\n\n"
                "Example: <code>pay Payments Support</code>\n\n"
                "<blockquote>❌ Send /cancel to abort.</blockquote>\n"
                f"{HR}"
            ),
            context="projects:from_template",
            args={"template_slug": template_slug},
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    if action == "blank":
        ctx = get_context(client)
        await akc.ask(
            client,
            ctx.db,
            chat_id=cq.message.chat.id,
            user_id=cq.from_user.id,
            text=(
                f"<b>📄 New blank project</b>\n"
                f"{HR}\n"
                "Send the new project's <b>slug</b> and optional <b>display "
                "name</b>, separated by a space.\n\n"
                "Example: <code>feedback User Feedback</code>\n\n"
                "<blockquote>💡 Blank projects have no macros / KB / routing "
                "seeded — set those up yourself after creation, or use "
                "<b>From template</b> instead.</blockquote>\n"
                f"{HR}"
            ),
            context="projects:blank",
            edit_message_id=cq.message.id,
        )
        await cq.answer()
        return

    await cq.answer()


# ---------------------------------------------------------------------------
# AskAndConfirm handlers
# ---------------------------------------------------------------------------
async def _state_for(ctx, user_id: int) -> akc.AkcState | None:
    return akc.extract(await users_repo.get(ctx.db, user_id))


async def _on_from_template(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    template_slug = str(args.get("template_slug") or "")
    template = default_registry.get(template_slug)
    if template is None:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Template vanished</b>\n{HR}\n"
                f"<code>{template_slug}</code> is no longer registered.\n"
                f"{HR}"
            ),
        )
        return
    parts = (message.text or "").strip().split(maxsplit=1)
    if not parts:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Need a slug</b>\n{HR}\n"
                "Format: <code>&lt;slug&gt; [name…]</code>\n"
                "Try again, or <code>/cancel</code>.\n"
                f"{HR}"
            ),
        )
        return
    slug = parts[0]
    name = parts[1] if len(parts) == 2 else template.name

    result = await install_template(
        ctx.db,
        ctx.bus,
        template=template,
        project_slug=slug,
        project_name=name,
        installed_by=message.from_user.id,
    )
    if not result.ok:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Install failed</b>\n{HR}\n"
                f"{result.detail or 'unknown error'}\n\n"
                "Try a different slug, or <code>/cancel</code>.\n"
                f"{HR}"
            ),
        )
        return
    hint = (
        f"<blockquote>{template.post_install_hint}</blockquote>"
        if template.post_install_hint
        else ""
    )
    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(
            f"<b>✅ Project created</b>\n{HR}\n"
            f"<b>{name}</b>  <code>{slug}</code>\n\n"
            f"• Macros seeded: {result.macros_seeded}\n"
            f"• KB articles seeded: {result.kb_articles_seeded}\n"
            f"• Routing rules seeded: {result.routing_rules_seeded}\n"
            f"{hint}\n"
            f"{HR}"
        ),
        keyboard=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "◀ Back to projects", callback_data="cb:v2:admin:projects:list"
                    )
                ]
            ]
        ),
    )


async def _on_blank(ctx, client: Client, message: Message, args: dict) -> None:
    state = await _state_for(ctx, message.from_user.id)
    if state is None:
        return
    parts = (message.text or "").strip().split(maxsplit=1)
    if not parts:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Need a slug</b>\n{HR}\n"
                "Format: <code>&lt;slug&gt; [name…]</code>\n"
                "Try again, or <code>/cancel</code>.\n"
                f"{HR}"
            ),
        )
        return
    slug = parts[0]
    name = parts[1] if len(parts) == 2 else slug

    existing = await ctx.db.projects.find_one({"slug": slug})
    if existing is not None:
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                f"<b>⚠️ Slug taken</b>\n{HR}\n"
                f"<code>{slug}</code> already exists. Pick a different slug, "
                f"or <code>/cancel</code>.\n{HR}"
            ),
        )
        return

    try:
        from xtv_support.utils.time import utcnow

        await ctx.db.projects.insert_one(
            {
                "slug": slug,
                "name": name,
                "description": "",
                "type": "support",
                "template_slug": None,
                "active": True,
                "created_at": utcnow(),
                "created_by": message.from_user.id,
                "ticket_count": 0,
            }
        )
    except Exception as exc:  # noqa: BLE001
        await akc.fail(
            client,
            ctx.db,
            user_id=message.from_user.id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=f"<b>⚠️ Error</b>\n{HR}\n<code>{exc}</code>\n{HR}",
        )
        return

    await akc.confirm(
        client,
        ctx.db,
        user_id=message.from_user.id,
        reply_chat_id=message.chat.id,
        reply_msg_id=message.id,
        state=state,
        confirmation_text=(
            f"<b>✅ Blank project created</b>\n{HR}\n"
            f"<b>{name}</b>  <code>{slug}</code>\n\n"
            "<blockquote>🛠 Seed macros / KB / routing from "
            "<code>/admin → 📁 Projects</code>.</blockquote>\n"
            f"{HR}"
        ),
        keyboard=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "◀ Back to projects", callback_data="cb:v2:admin:projects:list"
                    )
                ]
            ]
        ),
    )


akc.register("projects:from_template", _on_from_template)
akc.register("projects:blank", _on_blank)
