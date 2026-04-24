from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.callback_data import CbRate
from xtv_support.core.constants import CallbackPrefix, HandlerGroup, UserState
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix, is_admin_user, is_private, not_command
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import contact_links as contact_links_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.services.tickets import service as ticket_service
from xtv_support.ui.primitives.card import send_card
from xtv_support.ui.templates import user_messages
from xtv_support.utils.text import escape_html

log = get_logger("user.feedback")


@Client.on_message(
    is_private & ~is_admin_user & not_command,
    group=HandlerGroup.USER_FLOW,
)
async def user_message(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user_id = message.from_user.id

    state_doc = await users_repo.get(ctx.db, user_id)
    state = (state_doc or {}).get("state") or ""
    data = (state_doc or {}).get("data") or {}

    project = None
    contact_uuid: str | None = None
    target_admin_id: int | None = None

    if state == UserState.AWAITING_FEEDBACK:
        project = await projects_repo.get(ctx.db, data.get("project_id", ""))
    elif state == UserState.AWAITING_CONTACT_MSG:
        contact_uuid = data.get("contact_uuid")
        if contact_uuid:
            link = await contact_links_repo.get(ctx.db, contact_uuid)
            target_admin_id = (link or {}).get("admin_id")

    if project and project.get("type") == "feedback":
        await _handle_feedback_submission(client, message, project)
        await users_repo.clear_state(ctx.db, user_id)
        return

    if project or target_admin_id:
        try:
            ticket = await ticket_service.create_ticket_from_message(
                client,
                ctx.db,
                message=message,
                project=project,
                contact_uuid=contact_uuid,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("feedback.ticket_create_failed", user_id=user_id, error=str(exc))
            # Report into ERROR_LOG_TOPIC_ID so admins see the crash live.
            from xtv_support.handlers.errors import report_error
            from xtv_support.ui.primitives.card import Card

            try:
                await report_error(client, exc, context=f"ticket.create user={user_id}")
            except Exception:  # noqa: BLE001
                pass

            await send_card(
                client,
                user_id,
                Card(
                    title="⚠️ Something went wrong",
                    body=[
                        "We could not open your ticket right now.",
                        "The team has been notified, please try again in a moment.",
                    ],
                ),
            )
            return
        await users_repo.clear_state(ctx.db, user_id)
        if ticket and project and project.get("has_rating"):
            await send_card(client, user_id, user_messages.rating_card(str(project["_id"])))
        return

    # Look for an existing open ticket to forward the message into.
    existing = await tickets_repo.get_user_topic(ctx.db, user_id, None)
    if existing:
        await ticket_service.append_user_reply(client, ctx.db, ticket=existing, message=message)
        return

    await send_card(client, user_id, user_messages.please_start_card())


async def _handle_feedback_submission(client: Client, message: Message, project: dict) -> None:
    ctx = get_context(client)
    ticket = await ticket_service.create_ticket_from_message(
        client, ctx.db, message=message, project=project
    )
    # Feedback projects auto-close immediately.
    if ticket and ticket.get("_id"):
        await tickets_repo.close(
            ctx.db, ticket["_id"], closed_by=None, reason="feedback_submission"
        )
    if project.get("has_rating"):
        await send_card(
            client,
            message.from_user.id,
            user_messages.rating_card(str(project["_id"])),
        )


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_RATE))
async def rating_submitted(client: Client, callback: CallbackQuery) -> None:
    data = CbRate.unpack(callback.data)
    ctx = get_context(client)
    project = await projects_repo.get(ctx.db, data.project_id)
    if not project:
        await callback.answer()
        return

    topic_id = project.get("feedback_topic_id")
    if topic_id:
        try:
            user = callback.from_user
            stars = "⭐" * data.score
            first = user.first_name or "user"
            text = (
                f"⭐ <b>Rating received</b> • {escape_html(project.get('name', ''))}\n"
                f'User: <a href="tg://user?id={user.id}">{escape_html(first)}</a>\n'
                f"Score: {stars}"
            )
            from pyrogram.enums import ParseMode

            from xtv_support.config.settings import settings

            await client.send_message(
                settings.ADMIN_CHANNEL_ID,
                text,
                parse_mode=ParseMode.HTML,
                message_thread_id=int(topic_id),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("rating.forward_failed", error=str(exc))

    from xtv_support.ui.primitives.card import edit_card

    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        user_messages.rating_thanks(data.score),
    )
    await callback.answer()


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
