from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_CHANNEL_ID

# Handle incoming messages from users (Private chat, not commands)
@Client.on_message(filters.private & ~filters.command(["start", "panel", "help", "admin", "close", "history"]) & ~filters.user(ADMIN_CHANNEL_ID))
async def handle_user_message(client: Client, message: Message):
    user_id = message.from_user.id

    # Check if user is blocked
    if db.is_user_blocked(user_id):
        return

    # Check state
    state_doc = db.get_state(user_id)
    project_id = None
    target_admin_id = None
    contact_uuid = None

    # 1. Check explicit state (user just selected a project or contact link)
    if state_doc:
        state = state_doc.get("state")
        if state == "awaiting_feedback":
            project_id = state_doc["data"].get("project_id")
        elif state == "awaiting_contact_msg":
            contact_uuid = state_doc["data"].get("contact_uuid")
            # Resolve Admin ID from UUID
            link_doc = db.get_contact_link(contact_uuid)
            if link_doc:
                target_admin_id = link_doc["admin_id"]

    # 2. Check implicit state (User has an active conversation?)
    # ... (Same logic as before for Support Tickets) ...

    # --- FEEDBACK vs SUPPORT LOGIC ---

    project = None
    if project_id:
        project = db.get_project(project_id)

    # CASE A: Feedback Project (Collection Only)
    if project and project.get("type") == "feedback":
        await handle_feedback_submission(client, message, project, user_id)
        # Clear state after feedback is sent (Fire and Forget)
        db.clear_state(user_id)
        return

    # CASE B: Support Project or Contact Link
    await handle_support_ticket(client, message, project, target_admin_id, contact_uuid, user_id)


async def handle_feedback_submission(client: Client, message: Message, project, user_id):
    # Check constraints
    if not project.get("has_text") and message.text:
        # If text is disabled but user sent text... we might ignore or accept anyway.
        # Let's accept it to not annoy user.
        pass

    topic_id = project.get("feedback_topic_id", 13)

    msg_text = message.text or message.caption or "(Media)"
    msg_type = "text"
    file_id = None
    if message.photo:
        msg_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id

    # Create a Ticket for record keeping (closed immediately?) or just Log?
    # User said "Feedback and Support are completely different".
    # But we probably want to save it in DB.
    # We mark status="closed" immediately? or "feedback"?
    # Let's create a ticket with status "feedback" (requires DB update? or just use open and ignore).

    # Send to Sammel-Topic
    user_link = f"[{message.from_user.first_name}](tg://user?id={user_id})"
    caption = f"💬 **Feedback** ({project['name']})\n👤 {user_link}\n\n{msg_text}"

    try:
        if msg_type == "photo":
            await client.send_photo(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
        elif msg_type == "document":
            await client.send_document(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
        else:
            await client.send_message(ADMIN_CHANNEL_ID, caption, message_thread_id=topic_id)

        # Reply to User
        await message.reply_text("Thanks for your feedback! ❤️")

        # Rating?
        if project.get("has_rating"):
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⭐ 1", callback_data=f"rate_{project['_id']}_1"),
                    InlineKeyboardButton("⭐ 2", callback_data=f"rate_{project['_id']}_2"),
                    InlineKeyboardButton("⭐ 3", callback_data=f"rate_{project['_id']}_3"),
                    InlineKeyboardButton("⭐ 4", callback_data=f"rate_{project['_id']}_4"),
                    InlineKeyboardButton("⭐ 5", callback_data=f"rate_{project['_id']}_5")
                ]
            ])
            await message.reply_text("Please rate your experience:", reply_markup=buttons)

    except Exception as e:
        print(f"Error sending feedback: {e}")
        await message.reply_text("❌ Error sending feedback.")


async def handle_support_ticket(client: Client, message: Message, project, target_admin_id, contact_uuid, user_id):
    project_id = str(project['_id']) if project else None

    # 0. Check for existing open tickets with Topics
    existing_ticket = db.get_user_topic(user_id, project_id) if project_id else None

    # If Contact Mode: Don't append to random tickets, unless it's the SAME contact session?
    # But contact session is stateless after first message? Or do we keep it open?
    # Plan: Contact starts a ticket. Subsequent messages append if ticket is open.
    if not existing_ticket and not project_id and not target_admin_id:
         # Search any open ticket
         tickets = db.get_tickets_by_user(user_id)
         for t in tickets:
             if t['status'] == 'open' and t.get('topic_id'):
                 existing_ticket = t
                 break

    if existing_ticket and not target_admin_id:
         # Forward to Topic (Existing Logic)
         await forward_to_topic(client, message, existing_ticket)
         return

    if not project_id and not target_admin_id:
        await message.reply_text("⚠️ Please select a project first using /start")
        return

    # Create New Ticket
    msg_text = message.text or message.caption or "(Media)"
    msg_type = "text"
    file_id = None
    if message.photo:
        msg_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id

    ticket_id = db.create_ticket(project_id, user_id, msg_text, msg_type, file_id, contact_uuid=contact_uuid)

    if not ticket_id:
        await message.reply_text("❌ Error creating ticket.")
        return

    # Notify Admin / Create Topic
    # We will AUTO-CREATE Topic for support tickets now, as implied by "Support Project" flow.
    # User said: "beim feedback projekt soll auch ein flow sein... beim support projekt ist es so wie bisher (eigenes topic pro user)"

    # Determine Topic Name
    if target_admin_id:
        link_doc = db.get_contact_link(contact_uuid)
        display_name = link_doc.get("display_name", "Admin")
        source_name = f"📞 Contact ({display_name})"
    else:
        source_name = project["name"]

    username = message.from_user.first_name
    topic_title = f"{username} | {source_name}"

    try:
        topic = await client.create_forum_topic(ADMIN_CHANNEL_ID, title=topic_title)
        db.set_ticket_topic(ticket_id, topic.id)

        # Send Initial Message to Topic
        info_text = (
            f"🎫 **New Ticket**\n"
            f"👤 User: [{username}](tg://user?id={user_id})\n"
            f"📂 Source: {source_name}\n"
            f"🆔 Ticket: `{ticket_id}`\n\n"
            f"💬: {msg_text}"
        )

        if target_admin_id:
            info_text += f"\n\n🔔 Attention: [Admin](tg://user?id={target_admin_id})"

        if msg_type == "photo":
            await client.send_photo(ADMIN_CHANNEL_ID, file_id, caption=info_text, message_thread_id=topic.id)
        elif msg_type == "document":
            await client.send_document(ADMIN_CHANNEL_ID, file_id, caption=info_text, message_thread_id=topic.id)
        else:
            await client.send_message(ADMIN_CHANNEL_ID, info_text, message_thread_id=topic.id)

        # Reply to User
        if target_admin_id:
             await message.reply_text("✅ Message sent. Please wait for a reply.")
        else:
             await message.reply_text("✅ Support Ticket created. We will get back to you soon.")

        # If Contact Link, clear state? Or keep?
        if target_admin_id:
            db.clear_state(user_id)

    except Exception as e:
        print(f"Error creating topic: {e}")
        await message.reply_text("❌ Error processing request.")


async def forward_to_topic(client, message, ticket):
    msg_text = message.text or message.caption or "(Media)"
    msg_type = "text"
    file_id = None
    if message.photo:
        msg_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id

    db.add_message_to_ticket(ticket['_id'], "user", msg_text, msg_type, file_id)

    topic_id = ticket['topic_id']
    caption = f"👤 **User:**\n{msg_text}"

    try:
        if msg_type == "photo":
            await client.send_photo(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
        elif msg_type == "document":
            await client.send_document(ADMIN_CHANNEL_ID, file_id, caption=caption, message_thread_id=topic_id)
        else:
            await client.send_message(ADMIN_CHANNEL_ID, caption, message_thread_id=topic_id)
    except Exception as e:
        await message.reply_text(f"❌ Error delivering message: {e}")


# --- Rating Handler ---
@Client.on_callback_query(filters.regex("^rate_"))
async def rating_handler(client: Client, callback: CallbackQuery):
    # data: rate_projectid_score
    parts = callback.data.split("_")
    project_id = parts[1]
    score = int(parts[2])

    # Store rating? We need a DB method for ratings or add to last ticket?
    # Since Feedback tickets are 'fire and forget', maybe we just log it to the channel?
    project = db.get_project(project_id)
    topic_id = project.get("feedback_topic_id", 13)

    user_link = f"[{callback.from_user.first_name}](tg://user?id={callback.from_user.id})"

    try:
        await client.send_message(
            ADMIN_CHANNEL_ID,
            f"⭐ **New Rating**\n👤 {user_link} rated **{project['name']}**: {'⭐'*score}",
            message_thread_id=topic_id
        )
        await callback.message.edit_text(f"Thanks for rating {score} stars! ⭐")
    except:
        await callback.answer("Error sending rating.")
