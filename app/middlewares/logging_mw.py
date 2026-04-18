from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from app.constants import HandlerGroup
from app.core.logger import get_logger

log = get_logger("msg")
cb_log = get_logger("cb")


def _chat_type(message: Message) -> str:
    try:
        return str(message.chat.type) if message.chat else "?"
    except Exception:  # noqa: BLE001
        return "?"


def _short_text(message: Message, limit: int = 80) -> str:
    text = message.text or message.caption or ""
    if not text:
        if message.photo:
            return "[photo]"
        if message.document:
            return f"[document {getattr(message.document, 'file_name', '?')}]"
        if message.video:
            return "[video]"
        if message.sticker:
            return "[sticker]"
        if message.voice:
            return "[voice]"
        return "[no-text]"
    return text[:limit] + ("…" if len(text) > limit else "")


@Client.on_message(filters.all, group=HandlerGroup.MIDDLEWARE_LOG)
async def log_incoming(_client: Client, message: Message) -> None:
    user = message.from_user
    log.info(
        "msg.in",
        chat_id=message.chat.id if message.chat else None,
        chat_type=_chat_type(message),
        thread=message.message_thread_id,
        user_id=user.id if user else None,
        user=(f"@{user.username}" if user and user.username else (user.first_name if user else "?")),
        msg_id=message.id,
        text=_short_text(message),
    )


@Client.on_callback_query(filters.all, group=HandlerGroup.MIDDLEWARE_LOG)
async def log_callback(_client: Client, callback: CallbackQuery) -> None:
    user = callback.from_user
    cb_log.info(
        "cb.in",
        user_id=user.id if user else None,
        user=(f"@{user.username}" if user and user.username else (user.first_name if user else "?")),
        data=callback.data,
        chat_id=callback.message.chat.id if callback.message and callback.message.chat else None,
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
