from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_CHANNEL_ID

# --- 1. Reply via Button (Wizard) ---
@Client.on_callback_query(filters.regex("^admin_reply_"))
async def reply_button_click(client: Client, callback: CallbackQuery):
    ticket_id = callback.data.split("_")[-1]
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        await callback.answer("Ticket not found!", show_alert=True)
        return

    msg = await callback.message.reply_text(
        f"✍️ **Reply to User**\n\nTicket: `{ticket_id}`\n\nPlease type your message below. Type /cancel to abort.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_reply_cancel")]])
    )

    # Store state
    db.set_state(callback.from_user.id, "awaiting_admin_reply", {"ticket_id": str(ticket_id), "msg_id": msg.id})
    await callback.answer()

@Client.on_callback_query(filters.regex("^admin_reply_cancel"))
async def cancel_reply(client: Client, callback: CallbackQuery):
    db.clear_state(callback.from_user.id)
    await callback.message.delete()
    await callback.answer("Cancelled.")

# --- 2. Handle Admin Input for Button Reply ---
@Client.on_message(filters.private, group=2)
# Note: Admins answering in private chat (triggered by button)
async def handle_admin_reply_input(client: Client, message: Message):
    user_id = message.from_user.id
    state_doc = db.get_state(user_id)

    if not state_doc or state_doc.get("state") != "awaiting_admin_reply":
        return

    ticket_id = state_doc["data"]["ticket_id"]
    ticket = db.get_ticket(ticket_id)

    if message.text == "/cancel":
        db.clear_state(user_id)
        await message.reply_text("❌ Action cancelled.")
        return

    if not ticket:
        await message.reply_text("❌ Ticket no longer exists.")
        db.clear_state(user_id)
        return

    # Send to User
    await send_reply_to_user(client, ticket, message)

    # Clean up
    db.clear_state(user_id)
    await message.reply_text("✅ Reply sent to user.")


# --- 3. Handle Native Reply in Admin Topic ---
@Client.on_message(filters.chat(ADMIN_CHANNEL_ID))
async def handle_topic_reply(client: Client, message: Message):
    if not message.reply_to_message and not message.message_thread_id:
        return # Standard message in channel, ignore

    # Check if it's a topic reply
    if message.message_thread_id:
        topic_id = message.message_thread_id

        # Find ticket associated with this topic
        ticket = db.get_ticket_by_topic_id(topic_id)

        if ticket:
            # It's a reply in a ticket thread!
            await send_reply_to_user(client, ticket, message)
            # Maybe react to the message to confirm sending?
            # await message.react("👍") # Optional
            return

    # Check if it's a reply to a notification message (General Topic)
    if message.reply_to_message:
        # We need to find the ticket ID from the original message text or buttons?
        # Parsing text is flaky.
        # But wait, we can store mapping?
        # Actually, the notification message has buttons with ticket_id.
        # We can also parse the text "Ticket: `ID`"

        reply_to = message.reply_to_message
        if not reply_to.caption and not reply_to.text:
            return

        text = reply_to.caption or reply_to.text
        # Naive parsing
        import re
        match = re.search(r"Ticket: `([a-f0-9]+)`", text)
        if match:
            ticket_id = match.group(1)
            ticket = db.get_ticket(ticket_id)
            if ticket:
                 await send_reply_to_user(client, ticket, message)
                 return

async def send_reply_to_user(client: Client, ticket, message: Message):
    user_id = ticket['user_id']
    msg_text = message.text or message.caption or "(Media)"
    msg_type = "text"
    file_id = None

    if message.photo:
        msg_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id

    # Update DB History
    db.add_message_to_ticket(ticket['_id'], "admin", msg_text, msg_type, file_id)

    # Send to User
    formatted_text = f"👨‍💻 **Support:**\n\n{msg_text}"

    try:
        if msg_type == "photo":
            await client.send_photo(user_id, file_id, caption=formatted_text)
        elif msg_type == "document":
            await client.send_document(user_id, file_id, caption=formatted_text)
        else:
            await client.send_message(user_id, formatted_text)
    except Exception as e:
        print(f"Error sending to user: {e}")
        # Notify admin of failure?
        await message.reply_text(f"❌ Failed to send to user: {e}")
