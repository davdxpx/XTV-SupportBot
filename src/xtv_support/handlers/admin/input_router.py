from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from xtv_support.core.constants import (
    MAX_PROJECT_DESC_LEN,
    MAX_PROJECT_NAME_LEN,
    HandlerGroup,
    UserState,
)
from xtv_support.core.context import get_context
from xtv_support.core.filters import has_any_state, is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import audit as audit_repo
from xtv_support.infrastructure.db import contact_links as contact_links_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import tags as tags_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.ui.primitives.card import Card, send_card
from xtv_support.ui.templates import project_wizard

log = get_logger("admin.input_router")


@Client.on_message(
    is_admin_user & is_private & has_any_state, group=HandlerGroup.ADMIN_STATE
)
async def dispatch(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user_id = message.from_user.id
    state_doc = await users_repo.get(ctx.db, user_id) or {}
    state = state_doc.get("state", "")
    data = state_doc.get("data", {}) or {}

    text = message.text or ""

    if text == "/cancel":
        await users_repo.clear_state(ctx.db, user_id)
        await send_card(client, message.chat.id, Card(title="Cancelled", body=["The action was cancelled."]))
        message.stop_propagation()
        return

    handled = False

    if state == UserState.AWAITING_PROJECT_NAME:
        if len(text) == 0 or len(text) > MAX_PROJECT_NAME_LEN:
            await message.reply_text(f"Name must be 1..{MAX_PROJECT_NAME_LEN} characters.")
        else:
            await users_repo.set_state(
                ctx.db, user_id, UserState.AWAITING_PROJECT_DESC, {"name": text}
            )
            await send_card(client, message.chat.id, project_wizard.ask_description())
        handled = True

    elif state == UserState.AWAITING_PROJECT_DESC:
        if len(text) == 0 or len(text) > MAX_PROJECT_DESC_LEN:
            await message.reply_text(
                f"Description must be 1..{MAX_PROJECT_DESC_LEN} characters."
            )
        else:
            data["desc"] = text
            await users_repo.set_state(ctx.db, user_id, UserState.AWAITING_PROJECT_TYPE, data)
            await send_card(client, message.chat.id, project_wizard.ask_type())
        handled = True

    elif state == UserState.AWAITING_FEEDBACK_TOPIC:
        try:
            topic_id = int(text)
        except ValueError:
            await message.reply_text("Topic id must be a number. Try again or /cancel.")
            message.stop_propagation()
            return
        pid = await projects_repo.create(
            ctx.db,
            name=data["name"],
            description=data.get("desc", ""),
            created_by=user_id,
            project_type="feedback",
            feedback_topic_id=topic_id,
            has_rating=bool(data.get("has_rating")),
            has_text=bool(data.get("has_text", True)),
        )
        await users_repo.clear_state(ctx.db, user_id)
        await audit_repo.log(
            ctx.db, actor_id=user_id, action="project.create", target_id=str(pid)
        )
        await send_card(
            client, message.chat.id, project_wizard.done_feedback(data["name"])
        )
        handled = True

    elif state == UserState.AWAITING_CONTACT_NAME:
        display = text.strip()
        if not display:
            await message.reply_text("Name cannot be empty.")
            message.stop_propagation()
            return
        link = await contact_links_repo.create(
            ctx.db,
            admin_id=user_id,
            display_name=display,
            is_anonymous=bool(data.get("is_anonymous")),
        )
        me = await client.get_me()
        url = f"https://t.me/{me.username}?start=contact_{link}"
        await users_repo.clear_state(ctx.db, user_id)
        await audit_repo.log(
            ctx.db, actor_id=user_id, action="contact_link.create", target_id=link
        )
        await send_card(
            client,
            message.chat.id,
            Card(
                title="Contact link ready",
                body=[
                    f"Name: <b>{display}</b>",
                    f"Anonymous: {'yes' if data.get('is_anonymous') else 'no'}",
                    "",
                    f"Link: <code>{url}</code>",
                    "",
                    "Share this link. Users who open it will message you through the bot.",
                ],
            ),
        )
        handled = True

    elif state == UserState.AWAITING_BLOCK_ID:
        try:
            target = int(text.strip())
            await users_repo.block(ctx.db, target)
            await audit_repo.log(
                ctx.db, actor_id=user_id, action="user.block", target_id=str(target)
            )
            await send_card(
                client, message.chat.id, Card(title="Blocked", body=[f"User <code>{target}</code> is now blocked."])
            )
        except ValueError:
            await message.reply_text("Invalid user id.")
        await users_repo.clear_state(ctx.db, user_id)
        handled = True

    elif state == UserState.AWAITING_UNBLOCK_ID:
        try:
            target = int(text.strip())
            await users_repo.unblock(ctx.db, target)
            await audit_repo.log(
                ctx.db, actor_id=user_id, action="user.unblock", target_id=str(target)
            )
            await send_card(
                client,
                message.chat.id,
                Card(title="Unblocked", body=[f"User <code>{target}</code> is now unblocked."]),
            )
        except ValueError:
            await message.reply_text("Invalid user id.")
        await users_repo.clear_state(ctx.db, user_id)
        handled = True

    elif state == UserState.AWAITING_TAG_NAME:
        tag = text.strip().lower()
        if not tags_repo.valid_name(tag):
            await message.reply_text(
                "Tag must match <code>[a-z0-9_-]{1,24}</code>.", parse_mode="html"
            )
            message.stop_propagation()
            return
        await tags_repo.create(ctx.db, name=tag, created_by=user_id)
        await users_repo.clear_state(ctx.db, user_id)
        await audit_repo.log(ctx.db, actor_id=user_id, action="tag.create", target_id=tag)
        await send_card(
            client, message.chat.id, Card(title="Tag created", body=[f"#{tag}"])
        )
        handled = True

    if handled:
        message.stop_propagation()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
