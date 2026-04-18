from __future__ import annotations

from typing import Iterable

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def rows(*button_rows: Iterable[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(row) for row in button_rows])


def one(label: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=callback_data)]])


def url(label: str, href: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, url=href)


def btn(label: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, callback_data=callback_data)


def chunk(buttons: list[InlineKeyboardButton], per_row: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
