from __future__ import annotations

from typing import Callable

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.filters import Filter
from pyrogram.types import CallbackQuery, Message

from xtv_support.config.settings import settings

# --- Message filters ---


async def _is_admin_user_msg(_, __, m: Message) -> bool:
    return bool(m.from_user and m.from_user.id in settings.ADMIN_IDS)


is_admin_user = filters.create(_is_admin_user_msg, name="IsAdminUser")


async def _is_admin_channel(_, __, m: Message) -> bool:
    return m.chat is not None and m.chat.id == settings.ADMIN_CHANNEL_ID


is_admin_channel = filters.create(_is_admin_channel, name="IsAdminChannel")


async def _is_admin_topic(_, __, m: Message) -> bool:
    return (
        m.chat is not None
        and m.chat.id == settings.ADMIN_CHANNEL_ID
        and m.message_thread_id is not None
    )


is_admin_forum_topic = filters.create(_is_admin_topic, name="IsAdminForumTopic")


async def _is_private(_, __, m: Message) -> bool:
    return m.chat is not None and m.chat.type == ChatType.PRIVATE


is_private = filters.create(_is_private, name="IsPrivate")


def has_state(*state_names: str) -> Filter:
    """Match messages whose sender is in one of the given UserState values.

    Reads state from Mongo via the HandlerContext bound to the client.
    """
    wanted = set(state_names)

    async def _check(_, client, m: Message) -> bool:
        if not m.from_user:
            return False
        from xtv_support.core.context import get_context

        try:
            ctx = get_context(client)
        except RuntimeError:
            return False
        state_doc = await ctx.db.users.find_one(
            {"user_id": m.from_user.id},
            projection={"state": 1},
        )
        state = (state_doc or {}).get("state", "")
        return state in wanted

    return filters.create(_check, name=f"HasState({','.join(wanted) or '*'})")


async def _has_any_state(_, client, m: Message) -> bool:
    if not m.from_user:
        return False
    from xtv_support.core.context import get_context

    try:
        ctx = get_context(client)
    except RuntimeError:
        return False
    state_doc = await ctx.db.users.find_one(
        {"user_id": m.from_user.id},
        projection={"state": 1},
    )
    return bool((state_doc or {}).get("state"))


has_any_state = filters.create(_has_any_state, name="HasAnyState")


async def _not_command(_, __, m: Message) -> bool:
    text = m.text or m.caption or ""
    return not text.startswith("/")


not_command = filters.create(_not_command, name="NotCommand")


# --- Callback-query filters ---


def cb_prefix(prefix: str) -> Filter:
    """Match callback queries whose data starts with the given prefix (followed by SEP or end)."""
    from xtv_support.core.callback_data import SEP

    async def _check(_, __, cb: CallbackQuery) -> bool:
        if not cb.data:
            return False
        return cb.data == prefix or cb.data.startswith(prefix + SEP)

    return filters.create(_check, name=f"CbPrefix({prefix})")


async def _is_admin_callback(_, __, cb: CallbackQuery) -> bool:
    return bool(cb.from_user and cb.from_user.id in settings.ADMIN_IDS)


is_admin_callback = filters.create(_is_admin_callback, name="IsAdminCallback")


# --- Compositions ---


def admin_cb(prefix: str) -> Filter:
    return cb_prefix(prefix) & is_admin_callback


__all__ = [
    "admin_cb",
    "cb_prefix",
    "has_any_state",
    "has_state",
    "is_admin_callback",
    "is_admin_channel",
    "is_admin_forum_topic",
    "is_admin_user",
    "is_private",
    "not_command",
]

# Silence unused-import lint for Callable
_: Callable | None = None

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
