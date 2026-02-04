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
    try:
        user_info = await client.get_users(user_id)
        username = user_info.first_name or f"User {user_id}"
    except:
        username = f"User {user_id}"

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
        if ticket.get('type') == 'photo':
            await client.send_photo(ADMIN_CHANNEL_ID, ticket['file_id'], caption=info_text, message_thread_id=topic.id)
        elif ticket.get('type') == 'document':
            await client.send_document(ADMIN_CHANNEL_ID, ticket['file_id'], caption=info_text, message_thread_id=topic.id)
        else:
            await client.send_message(ADMIN_CHANNEL_ID, info_text, message_thread_id=topic.id)

        await callback.answer("Topic created successfully!", show_alert=True)

        # Notify User
        try:
            await client.send_message(
                user_id,
                "👨‍💻 **Support Agent Joined**\n\nA support agent has opened a dedicated channel for your issue. You can continue chatting here."
            )
        except:
            pass # User might have blocked bot

    except Exception as e:
        error_msg = str(e)
        print(f"Error creating topic: {error_msg}")
        if "CHAT_ADMIN_REQUIRED" in error_msg:
             await callback.answer("Bot needs 'Manage Topics' permission in Admin Group!", show_alert=True)
        elif "TOPICS_NOT_AVAILABLE" in error_msg:
             await callback.answer("Topics are not enabled in the Admin Group!", show_alert=True)
        else:
             await callback.answer(f"Error: {error_msg[:60]}", show_alert=True)
