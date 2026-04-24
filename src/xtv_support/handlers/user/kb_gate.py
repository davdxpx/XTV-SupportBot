"""Pre-ticket KB gate handler.

Runs *before* the ticket-creation flow so users can self-serve on
common questions. Two entry points:

* :func:`kb_gate_msg` — intercepts free-text messages in private chat
  when ``FEATURE_KB_GATE`` is on and the user is not currently inside
  a wizard (``state`` is empty). Presents up to 3 suggested articles
  as inline buttons; the ticket-creation flow is skipped only when
  the user explicitly clicks one.

* :func:`kb_gate_cb` — handles the three callback types:
  👍 (helpful), 👎 (not helpful) and 🙋 talk to a human.

``/humanplease`` in the user DM is a shortcut that jumps straight to
ticket creation, bypassing the gate for the next message.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from xtv_support.core.constants import CallbackPrefix, HandlerGroup, UserState
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix, is_private, not_command
from xtv_support.core.i18n import current_locale
from xtv_support.core.logger import get_logger
from xtv_support.domain.events import KbArticleDismissed, KbArticleHelpful
from xtv_support.domain.models.kb import KbArticle
from xtv_support.infrastructure.db import kb as kb_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.services.kb import gate as kb_gate

log = get_logger("kb_gate")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _feature_on(ctx) -> bool:
    flags = getattr(ctx, "flags", None)
    return bool(flags and flags.is_enabled("KB_GATE"))


def _build_keyboard(
    articles: tuple[KbArticle, ...],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for article in articles:
        rows.append(
            [
                InlineKeyboardButton(
                    f"📄 {article.title[:60]}",
                    callback_data=f"{CallbackPrefix.USER_KB_HELPFUL}:{article.slug}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                "🙋 Talk to a human",
                callback_data=f"{CallbackPrefix.USER_KB_HUMAN}",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


async def _gate_active(ctx, user_id: int) -> bool:
    """True iff the gate should intercept this user's message.

    Skip when:
    * the user is currently inside a wizard (persisted ``users.state``)
    * the user just asked for a human via /humanplease or the inline
      "Talk to a human" button (short-lived FSM flag ``kb_bypass``)
    """
    # 1) Persistent user state (admin wizards, feedback collection, …).
    user = await users_repo.get(ctx.db, user_id)
    db_state = str((user or {}).get("state") or "")
    if db_state not in ("", UserState.IDLE):
        return False

    # 2) Ephemeral FSM flag — cleared after 120s or after the next message.
    fsm = getattr(ctx, "state", None)
    if fsm is not None:
        flag = await fsm.current(user_id)
        if flag == "kb_bypass":
            await fsm.clear(user_id)  # one-shot
            return False
    return True


# ----------------------------------------------------------------------
# Message interceptor
# ----------------------------------------------------------------------
@Client.on_message(
    is_private & filters.text & not_command,
    group=HandlerGroup.USER_FLOW,
)
async def kb_gate_msg(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    if not _feature_on(ctx):
        return
    if not await _gate_active(ctx, message.from_user.id):
        return

    query = (message.text or "").strip()
    locale = current_locale.get() or ctx.settings.DEFAULT_LANG
    result = await kb_gate.evaluate(
        ctx.db,
        ctx.bus,
        user_id=message.from_user.id,
        query=query,
        lang=locale,
        default_lang=ctx.settings.DEFAULT_LANG,
        max_suggestions=3,
    )
    if not result.triggered:
        return

    # Render each article's title as a button; tapping one later shows
    # the body + records a view.
    await message.reply_text(
        "I found these articles that might help — tap one to view, "
        "or <b>Talk to a human</b> to open a ticket.",
        reply_markup=_build_keyboard(result.suggestions),
    )
    message.stop_propagation()  # prevents the normal ticket-open flow


# ----------------------------------------------------------------------
# Callback handlers
# ----------------------------------------------------------------------
@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_KB_HELPFUL), group=HandlerGroup.COMMAND)
async def kb_helpful_cb(client: Client, callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    ctx = get_context(client)
    payload = (callback.data or "").split(":", 2)
    if len(payload) < 3:
        await callback.answer("Invalid", show_alert=False)
        return
    slug = payload[2]

    article = await kb_repo.get_by_slug(ctx.db, slug)
    if article is None:
        await callback.answer("Article gone", show_alert=True)
        return

    await kb_repo.increment_views(ctx.db, slug)
    await ctx.bus.publish(
        KbArticleHelpful(
            article_id=article.id,
            slug=slug,
            user_id=callback.from_user.id,
        )
    )
    try:
        await callback.message.edit_text(
            f"<b>{article.title}</b>\n\n"
            f"<blockquote expandable>{article.body}</blockquote>\n\n"
            f"Did this answer your question?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Yes, thanks",
                            callback_data=f"{CallbackPrefix.USER_KB_HELPFUL}:_ack:{slug}",
                        ),
                        InlineKeyboardButton(
                            "🙋 I still need help",
                            callback_data=f"{CallbackPrefix.USER_KB_HUMAN}",
                        ),
                    ]
                ]
            ),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("kb_gate.edit_failed", error=str(exc))
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_KB_HUMAN), group=HandlerGroup.COMMAND)
async def kb_human_cb(client: Client, callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    ctx = get_context(client)
    await ctx.bus.publish(
        KbArticleDismissed(
            article_id=None,
            user_id=callback.from_user.id,
            query=None,
            reason="humanplease",
        )
    )
    try:
        await callback.message.edit_text(
            "Sure — send your next message and a support agent will "
            "pick it up. (The KB gate is disabled for your next message.)"
        )
    except Exception:  # noqa: BLE001
        pass
    # Mark the user as "skip gate for the next message" via a short-
    # lived FSM state so the interceptor above bails out.
    from xtv_support.core.state import StateMachine  # local to keep import light

    fsm: StateMachine = ctx.state
    if fsm is not None:
        await fsm.set(
            callback.from_user.id,
            value="kb_bypass",
            ttl_seconds=120,
        )
    await callback.answer()


@Client.on_message(
    filters.private & filters.command("humanplease"),
    group=HandlerGroup.COMMAND,
)
async def humanplease_cmd(client: Client, message: Message) -> None:
    """User-facing shortcut to bypass the KB gate on the next message."""
    if not message.from_user:
        return
    ctx = get_context(client)
    from xtv_support.core.state import StateMachine

    fsm: StateMachine = ctx.state
    if fsm is not None:
        await fsm.set(
            message.from_user.id,
            value="kb_bypass",
            ttl_seconds=120,
        )
    await ctx.bus.publish(
        KbArticleDismissed(
            article_id=None,
            user_id=message.from_user.id,
            query=None,
            reason="explicit",
        )
    )
    await message.reply_text(
        "👌 Got it. Your next message will skip the help suggestions "
        "and go straight to a support agent."
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
