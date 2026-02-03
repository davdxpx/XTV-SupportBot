from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from db import db
from config import ADMIN_CHANNEL_ID

STATE_WAITING_CONTACT = "waiting_contact"

@Client.on_message(filters.command("contact") & filters.private)
async def contact_command(client, message: Message):
    user_id = message.from_user.id
    db.set_state(user_id, STATE_WAITING_CONTACT)
    await message.reply_text(
        "**Contact Admin**\n\nPlease send your message below. It will be forwarded to the admin anonymously (to them) but they will see your details if they wish to reply.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="contact_cancel")]])
    )

@Client.on_callback_query(filters.regex("^contact_cancel"))
async def contact_cancel(client, callback):
    db.clear_state(callback.from_user.id)
    await callback.message.edit_text("❌ Contact cancelled.")
    await callback.answer()

@Client.on_message(filters.private & ~filters.command("start") & ~filters.command("admin") & ~filters.command("contact"))
async def contact_message_handler(client, message: Message):
    # This handler overlaps with the feedback text handler in user.py
    # Pyrogram handlers are executed in order of registration (import order) or group.
    # To avoid conflict, I should check state here explicitly.
    # Or better, I can group them.
    # But since user.py also checks state, if state matches there, it handles it.
    # If state matches here, it handles it.

    user_id = message.from_user.id
    user_state = db.get_state(user_id)

    if not user_state or user_state.get("state") != STATE_WAITING_CONTACT:
        message.continue_propagation()
        return # Not for us

    # Forward to Admin Channel
    user = message.from_user
    user_link = f"[{user.first_name}](tg://user?id={user.id})"

    caption = f"📩 **New Contact Message**\nFrom: {user_link} (`{user.id}`)\n\n"

    # Send to channel
    # We use copy_message to preserve media if any, or send_message if text
    try:
        if message.text:
            sent_msg = await client.send_message(
                ADMIN_CHANNEL_ID,
                caption + message.text,
                disable_web_page_preview=True,
                protect_content=True
            )
        else:
            # Media
            sent_msg = await message.copy(
                ADMIN_CHANNEL_ID,
                caption=caption + (message.caption or ""),
                protect_content=True
            )

        # Save mapping
        db.save_contact_message(user_id, sent_msg.id)

        await message.reply_text("✅ Message sent to admin!")
        db.clear_state(user_id)

    except Exception as e:
        await message.reply_text(f"Error sending message: {e}")

@Client.on_message(filters.chat(ADMIN_CHANNEL_ID) & filters.reply)
async def admin_reply_handler(client, message: Message):
    # Check if the message being replied to is one of ours
    reply_to_id = message.reply_to_message_id

    contact_data = db.get_contact_owner(reply_to_id)
    if not contact_data:
        return # Not a reply to a contact message (or old/not tracked)

    user_id = contact_data["user_id"]

    try:
        # Forward admin's reply to user
        # We can anonymize the admin by just sending the content
        await message.copy(user_id)
        # Or customize: "Admin replied: ..."

        await message.reply_text(f"✅ Reply sent to user `{user_id}`!")

    except Exception as e:
        await message.reply_text(f"❌ Failed to send reply: {e}")
