"""Message-Surgery UI primitive — ``ask`` / ``confirm`` / ``fail``.

Core of the chat-cleanness pattern:

1. Admin taps a button in a card (``/admin`` panel).
2. Card handler calls :func:`ask` — bot sends the prompt card, stores
   ``{akc_context, akc_args, akc_prompt_chat, akc_prompt_msg}`` on the
   admin's FSM ``data`` bag and sets state to ``akc:<context>``.
3. Admin types the value.
4. The :mod:`xtv_support.handlers.admin.ask_confirm_router` catches the
   reply because the admin's state has the ``akc:`` prefix, looks up
   the registered async handler in :data:`HANDLERS`, and invokes it
   with ``(ctx, client, user_id, text, akc_args)``.
5. The handler either calls :func:`confirm` (→ delete reply + edit the
   prompt into a result card + clear state) or :func:`fail` (→ delete
   reply + edit the prompt to show the error, state stays armed for
   retry).

Net effect: the admin's DM stays clean — one live message per wizard
step, no stack of bot replies and no stale "send me the slug…"
prompts hanging around.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pyrogram import Client
    from pyrogram.types import InlineKeyboardMarkup


def _users_repo():
    """Lazy import — keeps this module importable in test sandboxes without motor."""
    from xtv_support.infrastructure.db import users as users_repo

    return users_repo


log = get_logger("ui.ask_and_confirm")

STATE_PREFIX = "akc:"

# Registry filled by feature modules at import time.
# Signature:
#   async (ctx, client, message, args) -> None
# — ``message`` is the pyrogram Message the admin just sent (gives chat_id,
# id, text). ``args`` is the bag the caller passed to :func:`ask`.
HandlerFn = Callable[[Any, "Client", Any, dict[str, Any]], Awaitable[None]]
HANDLERS: dict[str, HandlerFn] = {}


def register(context: str, handler: HandlerFn) -> None:
    """Register an ``on_value`` handler for a context key."""
    if not context:
        raise ValueError("context must be non-empty")
    HANDLERS[context] = handler


def resolve(context: str) -> HandlerFn | None:
    return HANDLERS.get(context)


@dataclass(frozen=True, slots=True)
class AkcState:
    context: str
    args: dict[str, Any]
    prompt_chat_id: int
    prompt_msg_id: int


# ---------------------------------------------------------------------------
# 1. ask — sends the prompt, arms the FSM
# ---------------------------------------------------------------------------
async def ask(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    chat_id: int,
    user_id: int,
    text: str,
    context: str,
    args: dict[str, Any] | None = None,
    keyboard: InlineKeyboardMarkup | None = None,
    edit_message_id: int | None = None,
) -> int:
    """Render the prompt card and arm the FSM.

    If ``edit_message_id`` is given, the current panel is edited in-place
    (the prompt replaces the panel). Otherwise a new message is sent.
    Returns the prompt message id for later bookkeeping.
    """
    from pyrogram.enums import ParseMode

    if edit_message_id is not None:
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            prompt_msg_id = edit_message_id
        except Exception as exc:  # noqa: BLE001 — fall back to a new message
            log.debug("akc.edit_fallback", error=str(exc))
            msg = await client.send_message(
                chat_id,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            prompt_msg_id = msg.id
    else:
        msg = await client.send_message(
            chat_id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        prompt_msg_id = msg.id

    await _users_repo().set_state(
        db,
        user_id,
        state=f"{STATE_PREFIX}{context}",
        data={
            "akc_context": context,
            "akc_args": dict(args or {}),
            "akc_prompt_chat": chat_id,
            "akc_prompt_msg": prompt_msg_id,
        },
    )
    log.debug("akc.ask", user_id=user_id, context=context, prompt_msg_id=prompt_msg_id)
    return prompt_msg_id


def extract(state_doc: dict[str, Any] | None) -> AkcState | None:
    """Pull the typed state out of a ``users`` document."""
    if state_doc is None:
        return None
    data = state_doc.get("data") or {}
    ctx = data.get("akc_context")
    chat = data.get("akc_prompt_chat")
    msg = data.get("akc_prompt_msg")
    if not ctx or chat is None or msg is None:
        return None
    return AkcState(
        context=str(ctx),
        args=dict(data.get("akc_args") or {}),
        prompt_chat_id=int(chat),
        prompt_msg_id=int(msg),
    )


# ---------------------------------------------------------------------------
# 2. confirm / fail — the actual "message surgery"
# ---------------------------------------------------------------------------
async def _delete_reply(client: Client, chat_id: int, message_id: int) -> None:
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as exc:  # noqa: BLE001
        log.debug("akc.delete_failed", error=str(exc))


async def _edit_prompt(
    client: Client,
    chat_id: int,
    message_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup | None,
) -> None:
    from pyrogram.enums import ParseMode
    from pyrogram.errors import MessageNotModified

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
    except Exception as exc:  # noqa: BLE001
        log.debug("akc.edit_failed", error=str(exc))


async def confirm(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    user_id: int,
    reply_chat_id: int,
    reply_msg_id: int,
    state: AkcState,
    confirmation_text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    clear_state: bool = True,
) -> None:
    """Happy path: delete the user's reply, edit the prompt to the result, clear FSM."""
    await _delete_reply(client, reply_chat_id, reply_msg_id)
    await _edit_prompt(
        client, state.prompt_chat_id, state.prompt_msg_id, confirmation_text, keyboard
    )
    if clear_state:
        await _users_repo().clear_state(db, user_id)


async def fail(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    user_id: int,
    reply_chat_id: int,
    reply_msg_id: int,
    state: AkcState,
    error_text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Soft error: delete reply, show error on prompt, keep state armed so user can retry."""
    await _delete_reply(client, reply_chat_id, reply_msg_id)
    await _edit_prompt(client, state.prompt_chat_id, state.prompt_msg_id, error_text, keyboard)
