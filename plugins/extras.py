from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_IDS, ADMIN_CHANNEL_ID

# --- Block User ---
@Client.on_callback_query(filters.regex("^admin_block_"))
async def block_user(client: Client, callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    db.block_user(user_id)
    await callback.answer("User blocked!", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None) # Remove buttons

# --- Close Ticket (Command) ---
@Client.on_message(filters.command("close"))
async def close_ticket_command(client: Client, message: Message):
    # Check context:
    # 1. User in Private Chat -> Close their active ticket
    # 2. Admin in Topic -> Close that ticket

    user_id = message.from_user.id

    # Case 2: Admin in Topic
    if message.chat.id == ADMIN_CHANNEL_ID and message.message_thread_id:
        topic_id = message.message_thread_id
        ticket = db.get_ticket_by_topic_id(topic_id)

        if ticket and ticket['status'] == 'open':
            db.close_ticket(ticket['_id'])
            await message.reply_text("✅ Ticket closed.")
            await client.close_forum_topic(ADMIN_CHANNEL_ID, topic_id)

            # Notify User
            try:
                await client.send_message(ticket['user_id'], "✅ **Ticket Closed**\n\nYour support ticket has been closed. If you need more help, simply send a new message.")
                db.clear_state(ticket['user_id'])
            except:
                pass
            return

    # Case 1: User in Private
    if message.chat.type == message.chat.type.PRIVATE:
        # Find active ticket
        # We assume the most recent open one? Or check state?
        # Let's check state first
        state = db.get_state(user_id)
        if state and state.get("last_ticket_id"):
             ticket_id = state["last_ticket_id"]
             ticket = db.get_ticket(ticket_id)
             if ticket and ticket['status'] == 'open':
                 db.close_ticket(ticket['_id'])
                 await message.reply_text("✅ Ticket closed. Thank you!")

                 # Close topic if exists
                 if ticket.get('topic_id'):
                     try:
                         await client.close_forum_topic(ADMIN_CHANNEL_ID, ticket['topic_id'])
                         await client.send_message(ADMIN_CHANNEL_ID, "🔒 User closed the ticket.", message_thread_id=ticket['topic_id'])
                     except:
                         pass
                 return

        # Fallback search
        tickets = db.get_tickets_by_user(user_id)
        for t in tickets:
            if t['status'] == 'open':
                db.close_ticket(t['_id'])
                await message.reply_text(f"✅ Ticket `{str(t['_id'])[-4:]}` closed.")
                if t.get('topic_id'):
                     try:
                         await client.close_forum_topic(ADMIN_CHANNEL_ID, t['topic_id'])
                         await client.send_message(ADMIN_CHANNEL_ID, "🔒 User closed the ticket.", message_thread_id=t['topic_id'])
                     except:
                         pass
                return

        await message.reply_text("⚠️ No active open ticket found.")

# --- History Command (Admin) ---
@Client.on_message(filters.command("history") & filters.user(ADMIN_IDS))
async def history_command(client: Client, message: Message):
    # Usage: /history <user_id>
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: `/history <user_id>`")
        return

    try:
        target_id = int(message.command[1])
    except:
        await message.reply_text("⚠️ Invalid User ID")
        return

    tickets = db.get_tickets_by_user(target_id)
    if not tickets:
        await message.reply_text("📭 No history found for this user.")
        return

    text = f"📜 **History for {target_id}**\n\n"
    for t in tickets[:5]: # Last 5
        status = "🟢" if t['status'] == 'open' else "🔴"
        date = t['created_at'].strftime("%Y-%m-%d")
        text += f"{status} `{str(t['_id'])}` ({date})\nLast msg: {t['history'][-1]['text'][:20]}...\n\n"

    await message.reply_text(text)
