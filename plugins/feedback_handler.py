from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_CHANNEL_ID

# Handle incoming messages from users (Private chat, not commands)
@Client.on_message(filters.private & ~filters.command(["start", "panel", "help"]) & ~filters.user(ADMIN_CHANNEL_ID))
async def handle_user_message(client: Client, message: Message):
    user_id = message.from_user.id

    # Check if user is blocked
    if db.is_user_blocked(user_id):
        return # Ignore blocked users

    # Check state
    state_doc = db.get_state(user_id)
    project_id = None

    # 1. Check explicit state (user just selected a project or contact link)
    target_admin_id = None

    if state_doc:
        state = state_doc.get("state")
        if state == "awaiting_feedback":
            project_id = state_doc["data"].get("project_id")
        elif state == "awaiting_contact_msg":
            # This is a Contact Session
            target_admin_id = state_doc["data"].get("target_admin_id")

    # 2. Check implicit state (User has an active last project/ticket)
    if not project_id:
        # Maybe they are replying to an existing ticket?
        # Or we just assume the last active project.
        # For now, let's enforce project selection if no state.
        # But wait, if they have an open ticket, we should append to it.
        pass

    # Logic:
    # A. If user has an OPEN ticket with a TOPIC assigned -> Forward there.
    # B. If user has selected a project (State) -> Create NEW ticket.
    # C. If neither -> Ask to select project.

    # 0. Check for existing open tickets with Topics (Global check)
    # If a user sends a message and has an open ticket with a topic, we append to it.
    # (Simplified: User can only have one active "Conversation" at a time without explicit project selection)

    # Check for ANY open ticket with a topic for this user
    # We need a DB helper for this. Let's assume we search most recent.
    existing_ticket = db.get_user_topic(user_id, project_id) if project_id else None

    # If we didn't filter by project yet, try to find ANY active topic
    # NOTE: If user is in "awaiting_contact_msg", we do NOT want to append to random old tickets, we want a new Contact Ticket.
    if not existing_ticket and not project_id and not target_admin_id:
        # We need a new DB function or just search tickets
        tickets = db.get_tickets_by_user(user_id)
        for t in tickets:
            if t['status'] == 'open' and t.get('topic_id'):
                existing_ticket = t
                break

    if existing_ticket and not target_admin_id:
        # Forward to Topic
        msg_text = message.text or message.caption or "(Media)"
        msg_type = "text"
        file_id = None
        if message.photo:
            msg_type = "photo"
            file_id = message.photo.file_id
        elif message.document:
            msg_type = "document"
            file_id = message.document.file_id

        # Update DB history
        db.add_message_to_ticket(existing_ticket['_id'], "user", msg_text, msg_type, file_id)

        # Send to Admin Topic
        topic_id = existing_ticket['topic_id']
        caption = f"👤 **User:**\n{msg_text}"

        try:
            if msg_type == "photo":
                await client.send_photo(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
            elif msg_type == "document":
                await client.send_document(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
            else:
                await client.send_message(ADMIN_CHANNEL_ID, caption, message_thread_id=topic_id)

            # Silent success (double check marks?)
            # await message.reply_text("Sent.", quote=True)
        except Exception as e:
            await message.reply_text(f"❌ Error delivering message: {e}")

        return

    if not project_id and not target_admin_id:
        # Fallback: check if we can infer or ask
        # For now, just show start menu
        await message.reply_text("⚠️ Please select a project first using /start")
        return

    # Determine message content
    msg_text = message.text or message.caption or "(Media)"
    msg_type = "text"
    file_id = None

    if message.photo:
        msg_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id
    # Add other types as needed

    # Create Ticket
    # Note: If it's a Contact Request, we might not have a project_id.
    # We should support creating tickets without project_id or use a placeholder "Contact" project?
    # Better: Update db.create_ticket to allow None project_id if type is contact.

    if target_admin_id:
        # It's a Contact Ticket
        # We handle this specifically
        project_name = "📞 Private Contact"
        # We use a dummy ID or handle None in DB?
        # Let's assume we pass None as project_id
        ticket_id = db.create_ticket(None, user_id, msg_text, msg_type, file_id)
        # We might need to flag this ticket as "Contact" type in DB to avoid errors in listing
    else:
        ticket_id = db.create_ticket(project_id, user_id, msg_text, msg_type, file_id)

    if not ticket_id:
        await message.reply_text("❌ Error creating ticket.")
        return

    # Notify Admin Channel
    if target_admin_id:
        # Special Notification
        project_name = "📞 Private Contact"
        admin_mention = f"[{target_admin_id}](tg://user?id={target_admin_id})" # Or ping?
    else:
        project = db.get_project(project_id)
        project_name = project["name"] if project else "Unknown"

    user_link = f"[{message.from_user.first_name}](tg://user?id={user_id})"

    notification_text = (
        f"📩 **New Ticket**\n\n"
        f"👤 User: {user_link} (`{user_id}`)\n"
        f"📂 Source: **{project_name}**\n"
        f"🆔 Ticket: `{ticket_id}`\n\n"
        f"💬: {msg_text}"
    )

    if target_admin_id:
         notification_text += f"\n\n🔔 Attention: [Admin](tg://user?id={target_admin_id})"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Reply", callback_data=f"admin_reply_{ticket_id}"),
            InlineKeyboardButton("🗣 Create Topic", callback_data=f"admin_topic_{ticket_id}")
        ],
        [InlineKeyboardButton("🚫 Block User", callback_data=f"admin_block_{user_id}")]
    ])

    # Send to General Topic of Admin Channel
    # If media, send as media
    if msg_type == "photo":
        await client.send_photo(ADMIN_CHANNEL_ID, file_id, caption=notification_text, reply_markup=buttons)
    elif msg_type == "document":
        await client.send_document(ADMIN_CHANNEL_ID, file_id, caption=notification_text, reply_markup=buttons)
    else:
        await client.send_message(ADMIN_CHANNEL_ID, notification_text, reply_markup=buttons)

    # Confirm to User
    await message.reply_text(
        "✅ **Feedback Received!**\n\n"
        "Our team has been notified. We will get back to you shortly.\n"
        "You can use `/close` to close this ticket if solved."
    )

    # Clear "awaiting_feedback" state so next messages might be treated differently?
    # Or keep it so they can send more info?
    # Let's keep it for now, but update logic later to append to same ticket if open.
    # For this step, we just create tickets.
    db.clear_state(user_id)

    # Update user to be in "chatting" mode for this ticket?
    # We'll handle appending in the next steps.
