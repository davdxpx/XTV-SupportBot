from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from app.constants import CallbackPrefix, HandlerGroup, MAX_BROADCAST_LEN, UserState
from app.core.context import get_context
from app.core.filters import cb_prefix, has_state, is_admin_user, is_private
from app.core.logger import get_logger
from app.db import broadcasts as broadcasts_repo
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.ui.card import edit_card, send_card
from app.ui.templates import broadcast as broadcast_tmpl

log = get_logger("admin.broadcast")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_BROADCAST_START))
async def broadcast_start(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await users_repo.set_state(ctx.db, callback.from_user.id, UserState.AWAITING_BROADCAST)
    await edit_card(client, callback.message.chat.id, callback.message.id, broadcast_tmpl.prompt())
    await callback.answer()


@Client.on_message(
    is_admin_user & is_private & has_state(UserState.AWAITING_BROADCAST),
    group=HandlerGroup.ADMIN_STATE,
)
async def broadcast_input(client: Client, message: Message) -> None:
    ctx = get_context(client)
    text = message.text or ""
    if not text or text.startswith("/"):
        if text == "/cancel":
            await users_repo.clear_state(ctx.db, message.from_user.id)
            await send_card(
                client,
                message.chat.id,
                broadcast_tmpl.prompt().__class__(title="Cancelled", body=["Broadcast discarded."]),
            )
        message.stop_propagation()
        return
    if len(text) > MAX_BROADCAST_LEN:
        await message.reply_text(f"Too long. Max {MAX_BROADCAST_LEN} characters.")
        message.stop_propagation()
        return

    total = await users_repo.count(ctx.db, blocked=False)
    await users_repo.patch_state_data(ctx.db, message.from_user.id, {"text": text, "total": total})
    await send_card(client, message.chat.id, broadcast_tmpl.preview(text, total))
    message.stop_propagation()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_BROADCAST_CONFIRM))
async def broadcast_confirm(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    state = await users_repo.get(ctx.db, callback.from_user.id)
    data = (state or {}).get("data") or {}
    text = data.get("text")
    total = data.get("total") or 0
    if not text:
        await callback.answer("No draft found.", show_alert=True)
        return

    bid = await broadcasts_repo.create(
        ctx.db,
        admin_id=callback.from_user.id,
        text=text,
        total=total,
    )
    running_card = broadcast_tmpl.running(text, sent=0, failed=0, blocked=0, total=total)
    try:
        await edit_card(client, callback.message.chat.id, callback.message.id, running_card)
    except Exception:  # noqa: BLE001
        pass
    await ctx.broadcasts.start(
        bid=bid,
        text=text,
        total=total,
        progress_chat_id=callback.message.chat.id,
        progress_msg_id=callback.message.id,
    )
    await users_repo.clear_state(ctx.db, callback.from_user.id)
    await callback.answer("Broadcast started.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_BROADCAST_CANCEL))
async def broadcast_cancel(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    if ctx.broadcasts.active:
        await ctx.broadcasts.cancel()
        await callback.answer("Cancelling…")
    else:
        await users_repo.clear_state(ctx.db, callback.from_user.id)
        try:
            await callback.message.delete()
        except Exception:  # noqa: BLE001
            pass
        await callback.answer("Discarded.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_BROADCAST_PAUSE))
async def broadcast_pause(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await ctx.broadcasts.pause()
    await callback.answer("Paused.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_BROADCAST_RESUME))
async def broadcast_resume(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await ctx.broadcasts.resume()
    await callback.answer("Resumed.")

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
