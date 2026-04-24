"""Central dispatcher for AskAndConfirm replies.

Every admin wizard that uses the message-surgery pattern registers an
``on_value`` handler in
:data:`xtv_support.ui.primitives.ask_and_confirm.HANDLERS`. When the
admin types a value while in an ``akc:*`` FSM state, this handler
picks it up (higher priority than the legacy ``input_router``), looks
the registered callback up, and invokes it with the extracted state.

Fails gracefully if no handler is registered for the context: clears
the state, leaves the chat clean.
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import has_state_prefix, is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.ui.primitives import ask_and_confirm as akc

log = get_logger("admin.ask_confirm")


@Client.on_message(
    is_admin_user & is_private & has_state_prefix(akc.STATE_PREFIX),
    # One group tighter than the legacy input_router so this runs first.
    group=HandlerGroup.ADMIN_STATE - 1,
)
async def dispatch(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user_id = message.from_user.id if message.from_user else 0
    text = (message.text or "").strip()

    if text == "/cancel":
        await users_repo.clear_state(ctx.db, user_id)
        # Best-effort delete of the cancel command so the chat stays tidy.
        try:
            await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
        except Exception:  # noqa: BLE001
            pass
        return

    state_doc = await users_repo.get(ctx.db, user_id)
    state = akc.extract(state_doc)
    if state is None:
        # State value has the akc: prefix but the data bag is missing —
        # shouldn't happen in practice. Clear it so the user isn't stuck.
        await users_repo.clear_state(ctx.db, user_id)
        return

    handler = akc.resolve(state.context)
    if handler is None:
        log.warning("akc.no_handler", context=state.context, user_id=user_id)
        await akc.fail(
            client,
            ctx.db,
            user_id=user_id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=(
                "<b>⚠️ Internal error</b>\nNo handler is registered for this wizard step. "
                "The state has been cleared — please try again from the menu."
            ),
        )
        await users_repo.clear_state(ctx.db, user_id)
        return

    try:
        await handler(ctx, client, message, state.args)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "akc.handler_raised",
            context=state.context,
            user_id=user_id,
            error=str(exc),
        )
        await akc.fail(
            client,
            ctx.db,
            user_id=user_id,
            reply_chat_id=message.chat.id,
            reply_msg_id=message.id,
            state=state,
            error_text=f"<b>⚠️ Error</b>\n<code>{exc}</code>\n\nTry again, or <code>/cancel</code> to abort.",
        )
