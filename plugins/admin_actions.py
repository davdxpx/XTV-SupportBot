from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_CHANNEL_ID

@Client.on_callback_query(filters.regex("^admin_topic_"))
async def create_ticket_topic(client: Client, callback: CallbackQuery):
    ticket_id = callback.data.split("_")[-1]
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        await callback.answer("Ticket not found.", show_alert=True)
        return

    if ticket.get("topic_id"):
        await callback.answer("Topic already exists!", show_alert=True)
        return

    user_id = ticket['user_id']
    user_info = await client.get_users(user_id)
    username = user_info.first_name or f"User {user_id}"
    project = db.get_project(ticket['project_id'])
    project_name = project['name'] if project else "Project"

    # Create Forum Topic
    try:
        topic = await client.create_forum_topic(
            chat_id=ADMIN_CHANNEL_ID,
            title=f"{username} | {project_name}"
        )

        # Save topic ID to ticket
        db.set_ticket_topic(ticket['_id'], topic.id)

        # Post initial info in the topic
        info_text = (
            f"🎫 **Ticket Support Thread**\n\n"
            f"👤 User: [{username}](tg://user?id={user_id})\n"
            f"🆔 Ticket: `{ticket_id}`\n"
            f"📂 Project: {project_name}\n\n"
            f"📝 **Original Message:**\n"
            f"{ticket['message']}\n\n"
            "👇 **Admins:** Reply to messages here to answer the user."
        )

        # If original was media, resend it here
        if ticket['type'] == 'photo':
            await client.send_photo(ADMIN_CHANNEL_ID, ticket['file_id'], caption=info_text, message_thread_id=topic.id)
        elif ticket['type'] == 'document':
            await client.send_document(ADMIN_CHANNEL_ID, ticket['file_id'], caption=info_text, message_thread_id=topic.id)
        else:
            await client.send_message(ADMIN_CHANNEL_ID, info_text, message_thread_id=topic.id)

        await callback.answer("Topic created successfully!", show_alert=True)

        # Notify User
        await client.send_message(
            user_id,
            "👨‍💻 **Support Agent Joined**\n\nA support agent has opened a dedicated channel for your issue. You can continue chatting here."
        )

    except Exception as e:
        await callback.answer(f"Error creating topic: {e}", show_alert=True)

# Listener to forward User messages to Topic (if it exists)
# This needs to hook into the message handler we wrote earlier.
# I will need to update plugins/feedback_handler.py to check for existing topics first.
