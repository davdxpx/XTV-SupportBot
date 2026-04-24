from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import CallbackPrefix, HandlerGroup, UserState
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix, is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import contact_links as contact_links_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.ui.primitives.card import edit_card, send_card
from xtv_support.ui.templates import user_messages

log = get_logger("start")


@Client.on_message(filters.command("start") & is_private, group=HandlerGroup.COMMAND)
async def start_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user = message.from_user
    await users_repo.touch(
        ctx.db,
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )

    args = message.command
    if len(args) > 1:
        payload = args[1].strip()
        if payload.startswith("contact_"):
            link = await contact_links_repo.get(ctx.db, payload.removeprefix("contact_"))
            if link:
                await users_repo.set_state(
                    ctx.db,
                    user.id,
                    UserState.AWAITING_CONTACT_MSG,
                    {"contact_uuid": link["uuid"]},
                )
                display_name = link["display_name"]
                if not link.get("is_anonymous"):
                    try:
                        admin_user = await client.get_users(link["admin_id"])
                        display_name = admin_user.first_name or display_name
                    except Exception:  # noqa: BLE001
                        pass
                await send_card(
                    client,
                    user.id,
                    user_messages.contact_intro(display_name, link.get("is_anonymous", False)),
                )
                return

        project = await projects_repo.get(ctx.db, payload)
        if project and project.get("active"):
            await users_repo.set_state(
                ctx.db,
                user.id,
                UserState.AWAITING_FEEDBACK,
                {"project_id": str(project["_id"])},
            )
            await send_card(client, user.id, user_messages.project_intro(project))
            return

    await _send_project_selection(client, user.id)


async def _send_project_selection(client: Client, user_id: int) -> None:
    ctx = get_context(client)
    await users_repo.clear_state(ctx.db, user_id)
    projects = await projects_repo.list_active(ctx.db)
    if not projects:
        await send_card(client, user_id, user_messages.welcome_no_projects())
        return
    await send_card(client, user_id, user_messages.project_selection(projects))


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_SELECT_PROJECT))
async def project_selected(client: Client, callback: CallbackQuery) -> None:
    ctx = get_context(client)
    _, project_id = callback.data.split("|", 1)
    project = await projects_repo.get(ctx.db, project_id)
    if not project or not project.get("active"):
        await callback.answer("Project not available.", show_alert=True)
        return
    await users_repo.set_state(
        ctx.db,
        callback.from_user.id,
        UserState.AWAITING_FEEDBACK,
        {"project_id": str(project["_id"])},
    )
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        user_messages.project_intro(project),
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
