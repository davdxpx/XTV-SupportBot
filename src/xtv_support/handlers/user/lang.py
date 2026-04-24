"""/lang command + language-picker callback.

User sends ``/lang`` in DM -> we render an inline keyboard listing every
supported locale (flag + native name). Tapping a button persists the
choice on ``users.lang`` and acknowledges in the *just-picked* language
so the effect is immediately visible.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from xtv_support.config.i18n import list_supported
from xtv_support.core.constants import CallbackPrefix, HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix
from xtv_support.core.i18n import current_locale
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import users as users_repo

log = get_logger("lang")


def _build_keyboard(locales: dict[str, dict]) -> InlineKeyboardMarkup:
    """Two buttons per row, flag + native name."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for code, native, flag in list_supported(locales):
        label = f"{flag} {native}".strip() if flag else native
        row.append(
            InlineKeyboardButton(label, callback_data=f"{CallbackPrefix.USER_LANG_PICK}:{code}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


@Client.on_message(filters.private & filters.command("lang"), group=HandlerGroup.COMMAND)
async def lang_command(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    i18n = getattr(ctx, "i18n", None)
    locale = current_locale.get() or (i18n.default_lang if i18n is not None else "en")

    if i18n is None or not i18n.supported():
        await message.reply_text("Language picker is unavailable right now.")
        return

    header = i18n.t("user.language_list_header", locale=locale)
    locales = {code: i18n.locale(code) or {} for code in i18n.supported()}
    await message.reply_text(header, reply_markup=_build_keyboard(locales))


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_LANG_PICK), group=HandlerGroup.COMMAND)
async def lang_pick(client: Client, callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    i18n = getattr(ctx, "i18n", None)
    if i18n is None:
        await callback.answer("i18n unavailable", show_alert=False)
        return

    # callback.data = "u:lang:<code>"
    payload = (callback.data or "").split(":", 2)
    if len(payload) < 3:
        await callback.answer("Invalid", show_alert=False)
        return
    code = payload[2]
    if code not in i18n.supported():
        await callback.answer("Unsupported language", show_alert=True)
        return

    await users_repo.set_preferred_lang(ctx.db, callback.from_user.id, code)
    current_locale.set(code)

    meta = (i18n.locale(code) or {}).get("meta") or {}
    native = meta.get("native_name") or code
    ack = i18n.t("user.language_changed", locale=code, lang=native)
    try:
        await callback.message.edit_text(ack)  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — edit may fail (message too old); fall back to answer
        await callback.answer(ack, show_alert=False)
        return
    await callback.answer()
    log.info("lang.changed", user_id=callback.from_user.id, code=code)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
