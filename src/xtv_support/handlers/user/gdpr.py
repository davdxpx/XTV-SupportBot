"""GDPR user commands — ``/gdpr_export`` and ``/gdpr_delete``.

Wires the existing services in :mod:`xtv_support.services.gdpr` (the
exporter and deleter were already built; nothing was pointing at them
from the Telegram side). Keeps parity with the promises made by the
`/settings` panel's Export / Delete buttons.

- **``/gdpr_export``** — runs :func:`build_export` for the sender,
  uploads the JSON document back as a file. Safe to run repeatedly.
- **``/gdpr_delete``** — two-step flow:
    - First call → sends a warning card with a confirm inline button.
    - Confirm button → calls :func:`request_deletion`, which sets
      ``users.deleted_at`` and blocks the user; a periodic task
      (``purge_expired``) hard-deletes after the grace window
      (``DEFAULT_GRACE_DAYS`` = 30).
    - Running ``/gdpr_delete`` again inside the grace window restates
      the pending deletion instead of escalating.

Both commands are private-DM only; in topics they're no-ops.
"""

from __future__ import annotations

import io
import json

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_private
from xtv_support.core.logger import get_logger
from xtv_support.services.gdpr import deleter as gdpr_deleter
from xtv_support.services.gdpr import exporter as gdpr_exporter

log = get_logger("user.gdpr")


# ---------------------------------------------------------------------------
# /gdpr_export
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("gdpr_export") & is_private, group=HandlerGroup.COMMAND)
async def gdpr_export_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user_id = message.from_user.id if message.from_user else 0
    bundle = await gdpr_exporter.build_export(ctx.db, user_id)

    payload = json.dumps(bundle.to_json(), indent=2, default=str, ensure_ascii=False)
    buf = io.BytesIO(payload.encode("utf-8"))
    buf.name = f"xtv_export_{user_id}.json"

    await client.send_document(
        chat_id=message.chat.id,
        document=buf,
        caption=(
            "<b>📥 Your data export</b>\n\n"
            f"Generated at <i>{bundle.generated_at.isoformat()}</i>.\n"
            "Every section the bot stores about you, as JSON."
        ),
        parse_mode=ParseMode.HTML,
    )
    log.info("gdpr.export.delivered", user_id=user_id, sections=len(bundle.sections))


# ---------------------------------------------------------------------------
# /gdpr_delete — two-step
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("gdpr_delete") & is_private, group=HandlerGroup.COMMAND)
async def gdpr_delete_cmd(client: Client, message: Message) -> None:
    await client.send_message(
        message.chat.id,
        text=(
            "<b>🗑 Delete my data</b>\n\n"
            "This schedules a <b>hard delete</b> of every record the bot keeps "
            f"about you (tickets, messages, CSAT, audit entries) after "
            f"{gdpr_deleter.DEFAULT_GRACE_DAYS} days.\n\n"
            "You will be <b>blocked from the bot immediately</b>. You can "
            "cancel within the grace window by contacting an admin.\n\n"
            "This is irreversible after the grace window."
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Yes, delete my data",
                        callback_data="cb:v2:gdpr:confirm",
                    ),
                    InlineKeyboardButton(
                        "◀ Cancel",
                        callback_data="cb:v2:gdpr:abort",
                    ),
                ]
            ]
        ),
    )


@Client.on_callback_query(filters.regex(r"^cb:v2:gdpr:"), group=HandlerGroup.COMMAND)
async def gdpr_confirm_cb(client: Client, cq: CallbackQuery) -> None:
    action = (cq.data or "").split(":")[-1]
    user_id = cq.from_user.id if cq.from_user else 0

    if action == "abort":
        try:
            await cq.message.edit_text(
                "<i>Deletion cancelled.</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:  # noqa: BLE001
            pass
        await cq.answer("Cancelled.", show_alert=False)
        return

    if action != "confirm":
        await cq.answer()
        return

    ctx = get_context(client)
    receipt = await gdpr_deleter.request_deletion(ctx.db, user_id=user_id)
    log.info("gdpr.delete.requested", user_id=user_id, purge_at=receipt.purge_at.isoformat())
    try:
        await cq.message.edit_text(
            (
                "<b>🗑 Deletion scheduled</b>\n\n"
                f"Your data will be hard-deleted on "
                f"<b>{receipt.purge_at.strftime('%Y-%m-%d')}</b>.\n\n"
                "You are blocked from the bot starting now. Contact an admin "
                "inside the grace window if you change your mind."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:  # noqa: BLE001
        pass
    await cq.answer("Deletion scheduled.", show_alert=False)
