from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Sequence

from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, Message

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger
from xtv_support.ui.primitives.progress import bar as progress_bar
from xtv_support.ui.primitives.progress import percentage as pct_str

log = get_logger("ui")


def _strip(s: str | None) -> str:
    return (s or "").rstrip()


def _blockquote(inner: str, *, expandable: bool = False) -> str:
    tag = "<blockquote expandable>" if expandable else "<blockquote>"
    return f"{tag}{inner}</blockquote>"


@dataclass
class Card:
    """Composable message card.

    Structure (in render order, each section optional):

        <b>{title}</b>
        {step_line}          (e.g. "Step 2/4 • Status")
                             (blank line between sections)
        {body line 1}
        {body line 2}
        ...
        <blockquote>{quote}</blockquote>   ← only if ``quote`` is set
        {footer}

    Blockquote is intentionally reserved for ONE optional quoted section
    per card (e.g. the user's original message, a highlighted tip, etc.) —
    never for the whole message.
    """

    title: str
    body: Sequence[str] = field(default_factory=list)
    steps: tuple[int, int] | None = None
    status_line: str | None = None
    quote: str | None = None
    quote_expandable: bool = False
    footer: str | None = None
    buttons: InlineKeyboardMarkup | None = None

    def _lines(self) -> list[str]:
        lines: list[str] = [f"<b>{self.title}</b>"]
        if self.steps is not None:
            cur, total = self.steps
            suffix = f" • {self.status_line}" if self.status_line else ""
            lines.append(f"Step {cur}/{total}{suffix}")
        if self.body:
            lines.append("")
            lines.extend(_strip(line) for line in self.body)
        if self.quote:
            lines.append("")
            lines.append(_blockquote(self.quote, expandable=self.quote_expandable))
        if self.footer:
            lines.append("")
            lines.append(self.footer)
        return lines

    def render(self) -> tuple[str, InlineKeyboardMarkup | None]:
        return "\n".join(self._lines()), self.buttons


@dataclass
class ProgressCard(Card):
    """A Card with a live-editable progress strip.

    The progress bar is rendered inside a short ``<blockquote>`` so it pops
    visually without drowning the whole message in a quote.
    """

    progress: float = 0.0
    progress_label: str = "Progress"
    progress_width: int = 10

    _message_id: int | None = None
    _chat_id: int | None = None
    _thread_id: int | None = None
    _last_edit_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _closed: bool = False

    def _progress_strip(self) -> str:
        pct = pct_str(self.progress)
        bar = progress_bar(self.progress, width=self.progress_width)
        return _blockquote(f"{self.progress_label}: {pct}\n{bar}")

    def render(self) -> tuple[str, InlineKeyboardMarkup | None]:
        lines: list[str] = [f"<b>{self.title}</b>"]
        if self.steps is not None:
            cur, total = self.steps
            suffix = f" • {self.status_line}" if self.status_line else ""
            lines.append(f"Step {cur}/{total}{suffix}")
        if self.body:
            lines.append("")
            lines.extend(_strip(line) for line in self.body)
        lines.append("")
        lines.append(self._progress_strip())
        if self.quote:
            lines.append("")
            lines.append(_blockquote(self.quote, expandable=self.quote_expandable))
        if self.footer:
            lines.append("")
            lines.append(self.footer)
        return "\n".join(lines), self.buttons

    async def attach(
        self,
        client: Client,
        chat_id: int,
        *,
        thread_id: int | None = None,
    ) -> Message:
        text, keyboard = self.render()
        msg = await client.send_message(
            chat_id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            message_thread_id=thread_id,
            disable_web_page_preview=True,
        )
        self._message_id = msg.id
        self._chat_id = chat_id
        self._thread_id = thread_id
        self._last_edit_at = asyncio.get_event_loop().time()
        return msg

    async def update(
        self,
        client: Client,
        *,
        progress: float | None = None,
        status: str | None = None,
        body: Sequence[str] | None = None,
        footer: str | None = None,
        force: bool = False,
    ) -> None:
        if self._closed:
            return
        if progress is not None:
            self.progress = progress
        if status is not None:
            self.status_line = status
        if body is not None:
            self.body = body
        if footer is not None:
            self.footer = footer

        now = asyncio.get_event_loop().time()
        min_interval = settings.PROGRESS_EDIT_INTERVAL
        if not force and (now - self._last_edit_at) < min_interval:
            return

        async with self._lock:
            await self._do_edit(client)

    async def finalize(
        self,
        client: Client,
        *,
        status: str | None = None,
        footer: str | None = None,
        buttons: InlineKeyboardMarkup | None = None,
    ) -> None:
        if status is not None:
            self.status_line = status
        if footer is not None:
            self.footer = footer
        self.buttons = buttons
        async with self._lock:
            await self._do_edit(client)
        self._closed = True

    async def _do_edit(self, client: Client) -> None:
        if self._message_id is None or self._chat_id is None:
            return
        text, keyboard = self.render()
        try:
            await client.edit_message_text(
                chat_id=self._chat_id,
                message_id=self._message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            self._last_edit_at = asyncio.get_event_loop().time()
        except MessageNotModified:
            self._last_edit_at = asyncio.get_event_loop().time()
        except FloodWait as exc:
            wait = int(getattr(exc, "value", 1)) or 1
            log.warning("ui.progress.flood_wait", wait=wait)
            await asyncio.sleep(wait)


async def send_card(
    client: Client,
    chat_id: int,
    card: Card,
    *,
    thread_id: int | None = None,
    reply_to: int | None = None,
    **send_kwargs: Any,
) -> Message:
    text, keyboard = card.render()
    return await client.send_message(
        chat_id,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        message_thread_id=thread_id,
        reply_to_message_id=reply_to,
        disable_web_page_preview=True,
        **send_kwargs,
    )


async def edit_card(
    client: Client,
    chat_id: int,
    message_id: int,
    card: Card,
) -> None:
    text, keyboard = card.render()
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    except MessageNotModified:
        pass


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
