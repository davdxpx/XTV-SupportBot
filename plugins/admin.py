from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_IDS, ADMIN_CHANNEL_ID
import asyncio

# --- Main Admin Dashboard ---
# Allow commands in both Private and the Admin Channel (for convenience)
@Client.on_message(filters.command("admin") & filters.user(ADMIN_IDS) & (filters.private | filters.chat(ADMIN_CHANNEL_ID)))
async def admin_dashboard(client: Client, message: Message):
    await show_admin_dashboard(message)

async def show_admin_dashboard(message: Message | CallbackQuery):
    # Gather Stats
    total_projects = len(db.get_all_projects())
    total_users = db.users.count_documents({})
    total_tickets = db.tickets.count_documents({})

    text = (
        "🏢 **Admin Dashboard**\n\n"
        f"📊 **Statistics:**\n"
        f"• Projects: `{total_projects}`\n"
        f"• Users: `{total_users}`\n"
        f"• Tickets: `{total_tickets}`\n\n"
        "👇 **Select a module:**"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Manage Projects", callback_data="admin_projects")],
        [InlineKeyboardButton("🔗 Create Contact Link", callback_data="admin_create_contact")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users_menu")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ])

    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=buttons)
    else:
        await message.edit_message_text(text, reply_markup=buttons)

# --- 1. Manage Projects ---
@Client.on_callback_query(filters.regex("^admin_projects$") & filters.user(ADMIN_IDS))
async def manage_projects_menu(client: Client, callback: CallbackQuery):
    projects = db.get_all_projects()
    text = f"🗂 **Project Management**\n\nSelect a project to edit or create a new one."

    buttons_list = []
    for p in projects:
        status = "🟢" if p.get("active") else "🔴"
        type_icon = "💬" if p.get("type") == "feedback" else "🎫"
        buttons_list.append([InlineKeyboardButton(f"{status} {type_icon} {p['name']}", callback_data=f"admin_proj_view_{p['_id']}")])

    buttons_list.append([InlineKeyboardButton("➕ Create New Project", callback_data="admin_proj_create")])
    buttons_list.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back_main")])

    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons_list))

# --- Create Project Wizard ---
@Client.on_callback_query(filters.regex("^admin_proj_create$") & filters.user(ADMIN_IDS))
async def create_project_start(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text("📝 **New Project**\n\nEnter the **name**.\n/cancel to abort.")
    db.set_state(callback.from_user.id, "awaiting_project_name", {"msg_id": msg.id})

# --- View Project ---
@Client.on_callback_query(filters.regex("^admin_proj_view_") & filters.user(ADMIN_IDS))
async def view_project(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    project = db.get_project(project_id)
    if not project:
        await callback.answer("Project not found!", show_alert=True)
        return

    p_type = project.get("type", "support").title()
    rating = "✅" if project.get("has_rating") else "❌"
    text_fb = "✅" if project.get("has_text") else "❌"
    topic = project.get("feedback_topic_id") if project.get("type") == "feedback" else "N/A"

    text = (
        f"📂 **{project['name']}**\n"
        f"_{project['description']}_\n\n"
        f"Type: **{p_type}**\n"
        f"Tickets: {project.get('ticket_count', 0)}\n"
        f"Active: {'✅' if project.get('active') else '❌'}\n"
        f"ID: `{project['_id']}`\n\n"
        f"**Settings:**\n"
        f"Rating: {rating} | Text: {text_fb}\n"
        f"Target Topic: `{topic}`"
    )

    buttons = [
        [InlineKeyboardButton("📜 View Active Tickets", callback_data=f"admin_proj_tickets_{project_id}")],
        [InlineKeyboardButton("🗑 Delete Project", callback_data=f"admin_proj_delete_{project_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_projects")]
    ]
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_proj_tickets_") & filters.user(ADMIN_IDS))
async def view_project_tickets(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    tickets = db.get_tickets_by_project(project_id)
    open_tickets = [t for t in tickets if t['status'] == 'open']

    if not open_tickets:
        await callback.answer("No open tickets for this project.", show_alert=True)
        return

    text = f"📜 **Open Tickets**\n\n"
    for t in open_tickets[:10]:
        user_link = f"[{t['user_id']}](tg://user?id={t['user_id']})"
        text += f"🎫 `{str(t['_id'])[-4:]}` by {user_link}: {t['message'][:20]}...\n"

    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=f"admin_proj_view_{project_id}")]]
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_proj_delete_") & filters.user(ADMIN_IDS))
async def delete_project(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    db.delete_project(project_id)
    await callback.answer("Deleted!", show_alert=True)
    await manage_projects_menu(client, callback)


# --- 2. Create Contact Link (Wizard) ---
@Client.on_callback_query(filters.regex("^admin_create_contact$") & filters.user(ADMIN_IDS))
async def create_contact_link_start(client: Client, callback: CallbackQuery):
    text = "🔗 **Create Contact Link**\n\nShould this link be **Anonymous**?"
    buttons = [
        [InlineKeyboardButton("🕵️ Anonymous", callback_data="admin_contact_anon_yes")],
        [InlineKeyboardButton("👤 Public (Show my Name)", callback_data="admin_contact_anon_no")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back_main")]
    ]
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_contact_anon_"))
async def create_contact_link_name(client: Client, callback: CallbackQuery):
    anon = callback.data.endswith("yes")
    # Save partial state
    db.set_state(callback.from_user.id, "awaiting_contact_name", {"is_anonymous": anon})

    await callback.message.delete()
    prompt = "Enter a **Display Name** for this link (e.g. 'Support Agent', 'Max')."
    msg = await callback.message.reply_text(prompt)

    # Update state with msg_id to delete later if needed
    db.users.update_one({"user_id": callback.from_user.id}, {"$set": {"data.msg_id": msg.id}})


# --- 3. User Management ---
@Client.on_callback_query(filters.regex("^admin_users_menu$") & filters.user(ADMIN_IDS))
async def user_management_menu(client: Client, callback: CallbackQuery):
    text = "👥 **User Management**\n\nWhat would you like to do?"
    buttons = [
        [InlineKeyboardButton("🚫 Block User (ID)", callback_data="admin_users_block")],
        [InlineKeyboardButton("✅ Unblock User (ID)", callback_data="admin_users_unblock")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back_main")]
    ]
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_users_block$"))
async def prompt_block_user(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text("🚫 Send the **User ID** to block.")
    db.set_state(callback.from_user.id, "awaiting_block_id", {"msg_id": msg.id})

@Client.on_callback_query(filters.regex("^admin_users_unblock$"))
async def prompt_unblock_user(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text("✅ Send the **User ID** to unblock.")
    db.set_state(callback.from_user.id, "awaiting_unblock_id", {"msg_id": msg.id})


# --- 4. Broadcast ---
@Client.on_callback_query(filters.regex("^admin_broadcast$") & filters.user(ADMIN_IDS))
async def broadcast_prompt(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text(
        "📢 **Broadcast Message**\n\n"
        "Send the message (text, photo, etc.) you want to broadcast to ALL users.\n"
        "Type /cancel to abort."
    )
    db.set_state(callback.from_user.id, "awaiting_broadcast", {"msg_id": msg.id})


# --- Global Input Handler for Admin States ---
@Client.on_message(filters.user(ADMIN_IDS) & (filters.private | filters.chat(ADMIN_CHANNEL_ID)), group=5)
async def admin_input_handler(client: Client, message: Message):
    user_id = message.from_user.id
    state_doc = db.get_state(user_id)
    if not state_doc:
        return

    state = state_doc.get("state")
    data = state_doc.get("data", {})

    if message.text == "/cancel":
        db.clear_state(user_id)
        await message.reply_text("❌ Cancelled.")
        # Try to show dashboard again
        try:
             await show_admin_dashboard(message)
        except:
             pass
        return

    # --- Project Wizard ---
    if state == "awaiting_project_name":
        db.set_state(user_id, "awaiting_project_desc", {"name": message.text})
        await message.reply_text("✅ Name set. Now enter description.")
        return

    elif state == "awaiting_project_desc":
        desc = message.text
        name = data.get("name")
        # Ask for Project Type
        db.set_state(user_id, "awaiting_project_type", {"name": name, "desc": desc})

        buttons = [
            [InlineKeyboardButton("🎫 Support (Ticket System)", callback_data="admin_ptype_support")],
            [InlineKeyboardButton("💬 Feedback (Collection only)", callback_data="admin_ptype_feedback")]
        ]
        await message.reply_text("Is this a **Support** project or a **Feedback** project?", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # --- Contact Link Wizard ---
    elif state == "awaiting_contact_name":
        display_name = message.text
        is_anon = data.get("is_anonymous")

        # Create Link
        uuid_str = db.create_contact_link(user_id, display_name, is_anon)
        me = await client.get_me()
        link = f"https://t.me/{me.username}?start=contact_{uuid_str}"

        db.clear_state(user_id)
        await message.reply_text(
            f"🔗 **Contact Link Created**\n\n"
            f"Name: {display_name}\n"
            f"Anonymous: {'Yes' if is_anon else 'No'}\n"
            f"Link: `{link}`"
        )
        return

    # --- Block/Unblock ---
    elif state == "awaiting_block_id":
        try:
            target = int(message.text)
            db.block_user(target)
            await message.reply_text(f"🚫 User {target} blocked.")
        except:
            await message.reply_text("❌ Invalid ID.")
        db.clear_state(user_id)
        return
    elif state == "awaiting_unblock_id":
        try:
            target = int(message.text)
            db.users.update_one({"user_id": target}, {"$set": {"blocked": False}})
            await message.reply_text(f"✅ User {target} unblocked.")
        except:
            await message.reply_text("❌ Invalid ID.")
        db.clear_state(user_id)
        return

    # --- Broadcast ---
    elif state == "awaiting_broadcast":
        users = db.users.find({})
        count = 0
        failed = 0
        status_msg = await message.reply_text("📢 Sending broadcast...")

        for u in users:
            try:
                await message.copy(u['user_id'])
                count += 1
            except:
                failed += 1
            if count % 20 == 0:
                await asyncio.sleep(1)

        await status_msg.edit_text(f"✅ Broadcast complete.\nSent: {count}\nFailed: {failed}")
        db.clear_state(user_id)
        return

# --- Callback Handlers for Project Wizard ---
@Client.on_callback_query(filters.regex("^admin_ptype_"))
async def project_type_selected(client: Client, callback: CallbackQuery):
    ptype = callback.data.split("_")[-1] # support or feedback
    user_id = callback.from_user.id
    state_doc = db.get_state(user_id)

    if not state_doc or state_doc.get("state") != "awaiting_project_type":
        await callback.answer("Session expired.", show_alert=True)
        return

    data = state_doc["data"]
    data["type"] = ptype

    if ptype == "support":
        # Create immediately
        db.create_project(data["name"], data["desc"], user_id, project_type="support")
        db.clear_state(user_id)
        await callback.message.edit_text("🎉 **Support Project Created!**")
    else:
        # Feedback Flow
        db.set_state(user_id, "awaiting_feedback_rating", data)
        buttons = [
            [InlineKeyboardButton("✅ Yes", callback_data="admin_frating_yes")],
            [InlineKeyboardButton("❌ No", callback_data="admin_frating_no")]
        ]
        await callback.message.edit_text("Enable **Star Rating** (1-5)?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_frating_"))
async def feedback_rating_selected(client: Client, callback: CallbackQuery):
    has_rating = callback.data.endswith("yes")
    user_id = callback.from_user.id
    state_doc = db.get_state(user_id)

    if not state_doc: return
    data = state_doc["data"]
    data["has_rating"] = has_rating

    db.set_state(user_id, "awaiting_feedback_text", data)
    buttons = [
        [InlineKeyboardButton("✅ Yes", callback_data="admin_ftext_yes")],
        [InlineKeyboardButton("❌ No", callback_data="admin_ftext_no")]
    ]
    await callback.message.edit_text("Enable **Text Feedback**?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_ftext_"))
async def feedback_text_selected(client: Client, callback: CallbackQuery):
    has_text = callback.data.endswith("yes")
    user_id = callback.from_user.id
    state_doc = db.get_state(user_id)

    if not state_doc: return
    data = state_doc["data"]
    data["has_text"] = has_text

    # Ask for Topic ID
    db.set_state(user_id, "awaiting_feedback_topic", data)
    await callback.message.delete()
    await callback.message.reply_text("🔢 Please enter the **Topic ID** for this feedback channel (Default: `13`).\n\nSend `13` or any other ID.")

@Client.on_message(filters.user(ADMIN_IDS) & (filters.private | filters.chat(ADMIN_CHANNEL_ID)), group=6)
async def feedback_topic_handler(client: Client, message: Message):
    user_id = message.from_user.id
    state_doc = db.get_state(user_id)
    if not state_doc or state_doc.get("state") != "awaiting_feedback_topic":
        return

    try:
        topic_id = int(message.text)
    except:
        await message.reply_text("❌ Invalid ID. Using default 13.")
        topic_id = 13

    data = state_doc["data"]
    db.create_project(
        data["name"], data["desc"], user_id,
        project_type="feedback",
        feedback_topic_id=topic_id,
        has_rating=data["has_rating"],
        has_text=data["has_text"]
    )
    db.clear_state(user_id)
    await message.reply_text("🎉 **Feedback Project Created!**")


# --- Back Handlers ---
@Client.on_callback_query(filters.regex("^admin_back_main$"))
async def back_to_main_h(client: Client, callback: CallbackQuery):
    await show_admin_dashboard(callback)

@Client.on_callback_query(filters.regex("^admin_close$"))
async def close_panel_h(client: Client, callback: CallbackQuery):
    await callback.message.delete()
