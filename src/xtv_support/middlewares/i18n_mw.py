"""Per-update locale resolution.

Sets :data:`xtv_support.core.i18n.current_locale` (a ContextVar) at the
very start of each private-chat update so downstream handlers can call
:func:`xtv_support.core.i18n.tr` without threading the locale through
every signature.

Precedence
----------
1. The user's explicitly-chosen language (``users.lang`` — set via
   :command:`/lang` or the admin dashboard).
2. Telegram's ``user.language_code`` — normalised by stripping any
   regional suffix (``en-US`` -> ``en``) — but only if that code is in
   the bot's supported-locales list.
3. ``settings.DEFAULT_LANG`` (fallback).

The middleware runs in :attr:`HandlerGroup.MIDDLEWARE_GUARD` so it
arrives after ``logging_mw`` but before ``blocked_mw`` / ``cooldown_mw``
/ command handlers — every subsequent handler sees the right locale.
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_private
from xtv_support.core.i18n import current_locale, pick_locale
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import users as users_repo

log = get_logger("i18n_mw")


async def _resolve_locale(ctx, user_id: int, tg_language_code: str | None) -> str:
    """Per-update resolver — DB lookup + :func:`pick_locale`.

    The pure ranking logic lives in :func:`xtv_support.core.i18n.pick_locale`;
    this coroutine adds the single IO step (reading the user's persisted
    preference) and swallows DB errors so the dispatch never crashes just
    because Mongo hiccuped.
    """
    i18n = getattr(ctx, "i18n", None)
    default_lang = getattr(i18n, "default_lang", None) or ctx.settings.DEFAULT_LANG
    supported = i18n.supported() if i18n is not None else []

    try:
        preferred = await users_repo.get_preferred_lang(ctx.db, user_id)
    except Exception as exc:  # noqa: BLE001 — DB errors must not crash the dispatch
        log.debug("i18n.preferred_lookup_failed", user_id=user_id, error=str(exc))
        preferred = None

    return pick_locale(
        preferred=preferred,
        telegram_code=tg_language_code,
        supported=supported,
        default_lang=default_lang,
    )


@Client.on_message(is_private, group=HandlerGroup.MIDDLEWARE_GUARD)
async def set_locale_for_message(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    locale = await _resolve_locale(
        ctx, message.from_user.id, getattr(message.from_user, "language_code", None)
    )
    current_locale.set(locale)


@Client.on_callback_query(group=HandlerGroup.MIDDLEWARE_GUARD)
async def set_locale_for_callback(client: Client, callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    locale = await _resolve_locale(
        ctx, callback.from_user.id, getattr(callback.from_user, "language_code", None)
    )
    current_locale.set(locale)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
