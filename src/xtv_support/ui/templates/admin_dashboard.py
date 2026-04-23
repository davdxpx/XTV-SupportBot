from __future__ import annotations

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from xtv_support.core.constants import CallbackPrefix
from xtv_support.ui.primitives.card import Card
from xtv_support.ui.keyboards.base import btn


def dashboard(*, projects: int, users: int, tickets: int, open_tickets: int) -> Card:
    buttons = InlineKeyboardMarkup(
        [
            [btn("🗂 Manage Projects", CallbackPrefix.ADMIN_PROJECTS)],
            [btn("🔗 Create Contact Link", CallbackPrefix.ADMIN_CONTACT_START)],
            [btn("👥 User Management", CallbackPrefix.ADMIN_USERS)],
            [btn("🏷 Tags", CallbackPrefix.ADMIN_TAGS)],
            [btn("📢 Broadcast", CallbackPrefix.ADMIN_BROADCAST_START)],
            [btn("❌ Close", CallbackPrefix.ADMIN_CLOSE)],
        ]
    )
    return Card(
        title="🏢 Admin Dashboard",
        body=[
            f"📂 Projects: <b>{projects}</b>",
            f"👥 Users: <b>{users}</b>",
            f"🎫 Tickets: <b>{tickets}</b>  •  open: <b>{open_tickets}</b>",
        ],
        footer="<i>Select a module below.</i>",
        buttons=buttons,
    )


def project_list(projects: list[dict]) -> Card:
    rows_list: list[list[InlineKeyboardButton]] = []
    for p in projects:
        pid = str(p["_id"])
        active = bool(p.get("active"))
        ptype = p.get("type", "support")
        type_icon = "💬" if ptype == "feedback" else "🎫"
        status_icon = "🟢" if active else "🔴"
        name = p.get("name", "?")
        label = f"{status_icon} {type_icon} {name}"
        rows_list.append([btn(label, f"{CallbackPrefix.ADMIN_PROJECT_VIEW}|{pid}")])
    rows_list.append([btn("➕ Create new project", CallbackPrefix.ADMIN_PROJECT_CREATE)])
    rows_list.append([btn("🔙 Back", CallbackPrefix.ADMIN_HOME)])
    return Card(
        title="🗂 Project Management",
        body=["Choose a project or create a new one."],
        buttons=InlineKeyboardMarkup(rows_list),
    )


def project_detail(p: dict) -> Card:
    pid = str(p["_id"])
    rating = "on" if p.get("has_rating") else "off"
    has_text = "on" if p.get("has_text") else "off"
    topic = p.get("feedback_topic_id") if p.get("type") == "feedback" else "n/a"
    buttons = InlineKeyboardMarkup(
        [
            [btn("📜 View open tickets", f"{CallbackPrefix.ADMIN_PROJECT_TICKETS}|{pid}")],
            [btn("🗑 Delete project", f"{CallbackPrefix.ADMIN_PROJECT_DELETE}|{pid}")],
            [btn("🔙 Back", CallbackPrefix.ADMIN_PROJECTS)],
        ]
    )
    return Card(
        title=f"📂 Project • {p.get('name', '?')}",
        body=[
            f"<b>Type:</b> {p.get('type', 'support')}",
            f"<b>Tickets:</b> {p.get('ticket_count', 0)}",
            f"<b>Active:</b> {'yes' if p.get('active') else 'no'}",
            f"<b>Rating:</b> {rating}  •  <b>Text:</b> {has_text}",
            f"<b>Feedback topic id:</b> <code>{topic}</code>",
            f"<b>Id:</b> <code>{pid}</code>",
        ],
        quote=p.get("description") or None,
        buttons=buttons,
    )


def user_menu() -> Card:
    buttons = InlineKeyboardMarkup(
        [
            [btn("🚫 Block user", CallbackPrefix.ADMIN_USERS_BLOCK)],
            [btn("✅ Unblock user", CallbackPrefix.ADMIN_USERS_UNBLOCK)],
            [btn("🔙 Back", CallbackPrefix.ADMIN_HOME)],
        ]
    )
    return Card(title="👥 User Management", body=["Pick an action."], buttons=buttons)


def tags_menu(tags: list[dict]) -> Card:
    body = ["<b>Known tags:</b>"]
    if not tags:
        body.append("<i>(none yet)</i>")
    else:
        body.extend(f"• #{t['name']}" for t in tags)
    rows_list: list[list[InlineKeyboardButton]] = [
        [btn("➕ New tag", CallbackPrefix.ADMIN_TAG_NEW)],
    ]
    for t in tags[:20]:
        rows_list.append(
            [btn(f"🗑 Delete #{t['name']}", f"{CallbackPrefix.ADMIN_TAG_DEL}|{t['name']}")]
        )
    rows_list.append([btn("🔙 Back", CallbackPrefix.ADMIN_HOME)])
    return Card(title="🏷 Tag Management", body=body, buttons=InlineKeyboardMarkup(rows_list))


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
