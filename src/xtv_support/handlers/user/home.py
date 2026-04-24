"""User home / onboarding handlers — ``/home``, ``/faq``, ``/settings``.

The legacy ``/start`` handler in ``handlers/start.py`` stays
functionally unchanged for now; when
``FEATURE_NEW_ONBOARDING=true`` the ``/start`` command also opens the
new home panel. ``/home``, ``/faq``, ``/settings`` are always
available so users can get to the new UX even without flipping the
flag on.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_private
from xtv_support.core.logger import get_logger
from xtv_support.ui.primitives.card import edit_card, send_card
from xtv_support.ui.primitives.panel import Panel
from xtv_support.ui.templates.onboarding_panel import (
    HomeStats,
    faq_browse_panel,
    onboarding_panel,
    settings_panel,
)

log = get_logger("user.home")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
async def _collect_stats(db, user_id: int) -> HomeStats:
    from datetime import timedelta

    from xtv_support.utils.time import utcnow

    month_ago = utcnow() - timedelta(days=30)
    open_tickets = await db.tickets.count_documents(
        {"user_id": user_id, "status": "open"}
    )
    closed_month = await db.tickets.count_documents(
        {"user_id": user_id, "status": "closed", "closed_at": {"$gte": month_ago}}
    )
    waiting = await db.tickets.count_documents(
        {"user_id": user_id, "status": "open", "last_admin_msg_at": None}
    )
    return HomeStats(
        open_tickets=open_tickets,
        waiting_on_user=waiting,
        closed_this_month=closed_month,
    )


async def _unread_count(db, user_id: int) -> int:
    """Tickets with an admin reply the user hasn't seen yet.

    Approximation: admin msg is newer than the last time the user read
    this ticket. We don't track per-ticket read-cursors yet — a later
    phase adds that. For now count tickets where last_admin_msg_at >
    last_user_msg_at.
    """
    return await db.tickets.count_documents(
        {
            "user_id": user_id,
            "status": "open",
            "$expr": {
                "$gt": ["$last_admin_msg_at", "$last_user_msg_at"],
            },
        }
    )


async def _render_home_panel(client: Client, message: Message | None, cq: CallbackQuery | None) -> None:
    ctx = get_context(client)
    user = (message.from_user if message else cq.from_user) if (message or cq) else None
    if user is None:
        return

    stats = await _collect_stats(ctx.db, user.id)
    unread = await _unread_count(ctx.db, user.id)
    panel = onboarding_panel(
        user_first_name=user.first_name,
        unread_replies=unread,
        stats=stats,
    )

    await _send_or_edit(client, message, cq, panel)


async def _send_or_edit(
    client: Client,
    message: Message | None,
    cq: CallbackQuery | None,
    panel: Panel,
) -> None:
    text, keyboard = panel.render()
    if cq is not None and cq.message is not None:
        try:
            await cq.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        finally:
            await cq.answer()
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
# Command handlers
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("home") & is_private, group=HandlerGroup.COMMAND)
async def home_cmd(client: Client, message: Message) -> None:
    await _render_home_panel(client, message, None)


@Client.on_message(filters.command("faq") & is_private, group=HandlerGroup.COMMAND)
async def faq_cmd(client: Client, message: Message) -> None:
    await _render_faq(client, message, None, query=None)


async def _render_faq(
    client: Client,
    message: Message | None,
    cq: CallbackQuery | None,
    *,
    query: str | None,
) -> None:
    ctx = get_context(client)
    articles: list[tuple[str, str]] = []
    try:
        from xtv_support.services.kb.service import search as kb_search

        results = await kb_search(ctx.db, query=query or "", lang="en", limit=5)
        for art in results or []:
            body = str(art.get("body") or "")
            preview = body[:120] + ("…" if len(body) > 120 else "")
            articles.append((str(art.get("title") or ""), preview))
    except Exception as exc:  # noqa: BLE001
        log.debug("user.home.faq_fallback", error=str(exc))
    panel = faq_browse_panel(query=query, articles=articles)
    await _send_or_edit(client, message, cq, panel)


@Client.on_message(filters.command("settings") & is_private, group=HandlerGroup.COMMAND)
async def settings_cmd(client: Client, message: Message) -> None:
    await _render_settings(client, message, None)


async def _render_settings(
    client: Client, message: Message | None, cq: CallbackQuery | None
) -> None:
    ctx = get_context(client)
    user = (message.from_user if message else cq.from_user) if (message or cq) else None
    if user is None:
        return

    udoc = await ctx.db.users.find_one({"user_id": user.id}) or {}
    prefs = udoc.get("notification_prefs") or {}
    panel = settings_panel(
        language=str(udoc.get("lang") or ctx.settings.DEFAULT_LANG),
        notify_on_reply=bool(prefs.get("notify_reply", True)),
        notify_csat=bool(prefs.get("notify_csat", True)),
        notify_announcements=bool(prefs.get("notify_announcements", True)),
    )
    await _send_or_edit(client, message, cq, panel)


# ---------------------------------------------------------------------------
# Callback routing
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^cb:v2:home:"), group=HandlerGroup.COMMAND)
async def home_callback(client: Client, cq: CallbackQuery) -> None:
    data = (cq.data or "").split(":")
    # cb:v2:home:<action>
    action = data[3] if len(data) >= 4 else ""
    if action == "open":
        await _render_home_panel(client, None, cq)
    elif action == "faq":
        await _render_faq(client, None, cq, query=None)
    elif action == "settings":
        await _render_settings(client, None, cq)
    elif action == "new_ticket":
        await cq.answer(
            "Send your message here and we'll open a ticket. 📮", show_alert=False
        )
    elif action == "my_tickets":
        await cq.answer("Run /tickets to see your full list.", show_alert=False)
    else:
        await cq.answer()


@Client.on_callback_query(filters.regex(r"^cb:v2:faq:"), group=HandlerGroup.COMMAND)
async def faq_callback(client: Client, cq: CallbackQuery) -> None:
    data = (cq.data or "").split(":")
    action = data[3] if len(data) >= 4 else ""
    if action == "search":
        await cq.answer("Send a keyword message; I'll search the KB for you.", show_alert=False)
    else:
        await cq.answer()


@Client.on_callback_query(
    filters.regex(r"^cb:v2:settings:"), group=HandlerGroup.COMMAND
)
async def settings_callback(client: Client, cq: CallbackQuery) -> None:
    ctx = get_context(client)
    data = (cq.data or "").split(":")
    # cb:v2:settings:<action>[:<sub>]
    action = data[3] if len(data) >= 4 else ""
    sub = data[4] if len(data) >= 5 else ""
    user = cq.from_user
    if user is None:
        await cq.answer()
        return

    if action == "toggle":
        key = sub
        udoc = await ctx.db.users.find_one({"user_id": user.id}) or {}
        prefs = dict(udoc.get("notification_prefs") or {})
        current = bool(prefs.get(key, True))
        prefs[key] = not current
        await ctx.db.users.update_one(
            {"user_id": user.id},
            {"$set": {"notification_prefs": prefs}},
            upsert=True,
        )
        await _render_settings(client, None, cq)
        return

    if action == "lang":
        await cq.answer("Run /lang to change your language.", show_alert=False)
        return

    if action == "gdpr_export":
        await cq.answer(
            "Export requested — we'll DM you the archive shortly.", show_alert=True
        )
        return
    if action == "gdpr_delete":
        await cq.answer(
            "To confirm deletion, run /gdpr_delete. This is irreversible.",
            show_alert=True,
        )
        return

    await cq.answer()


# ---------------------------------------------------------------------------
# Opt-in: when FEATURE_NEW_ONBOARDING is true, hijack /start too.
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("start") & is_private, group=-1)
async def new_onboarding_start(client: Client, message: Message) -> None:
    ctx = get_context(client)
    if not ctx.flags or not getattr(ctx.flags, "NEW_ONBOARDING", False):
        return  # legacy /start handler will run
    await _render_home_panel(client, message, None)
    # Tell the legacy handler group 0 not to fire for this update.
    message.stop_propagation()
