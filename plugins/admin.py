from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_IDS
import asyncio

# --- Main Admin Dashboard ---
@Client.on_message(filters.command("admin") & filters.user(ADMIN_IDS) & filters.private)
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

# --- 1. Manage Projects (Existing Logic) ---
@Client.on_callback_query(filters.regex("^admin_projects$") & filters.user(ADMIN_IDS))
async def manage_projects_menu(client: Client, callback: CallbackQuery):
    projects = db.get_all_projects()
    text = f"🗂 **Project Management**\n\nSelect a project to edit or create a new one."

    buttons_list = []
    for p in projects:
        status = "🟢" if p.get("active") else "🔴"
        buttons_list.append([InlineKeyboardButton(f"{status} {p['name']}", callback_data=f"admin_proj_view_{p['_id']}")])

    buttons_list.append([InlineKeyboardButton("➕ Create New Project", callback_data="admin_proj_create")])
    buttons_list.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back_main")])

    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons_list))

# ... (Include the Create/View/Delete Project logic from previous admin_panel.py here, adapted if needed) ...
# I will rewrite the project handlers here to keep it self-contained.

@Client.on_callback_query(filters.regex("^admin_proj_create$") & filters.user(ADMIN_IDS))
async def create_project_start(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text("📝 **New Project**\n\nEnter the **name**.\n/cancel to abort.")
    db.set_state(callback.from_user.id, "awaiting_project_name", {"msg_id": msg.id})

@Client.on_callback_query(filters.regex("^admin_proj_view_") & filters.user(ADMIN_IDS))
async def view_project(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    project = db.get_project(project_id)
    if not project:
        await callback.answer("Project not found!", show_alert=True)
        return
    text = (
        f"📂 **{project['name']}**\n"
        f"_{project['description']}_\n\n"
        f"Tickets: {project.get('ticket_count', 0)}\n"
        f"ID: `{project['_id']}`"
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

    # Filter for open tickets only? Or all? Let's show open first.
    open_tickets = [t for t in tickets if t['status'] == 'open']

    if not open_tickets:
        await callback.answer("No open tickets for this project.", show_alert=True)
        return

    text = f"📜 **Open Tickets**\n\n"
    for t in open_tickets[:10]: # Limit 10
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


# --- 2. Create Contact Link ---
@Client.on_callback_query(filters.regex("^admin_create_contact$") & filters.user(ADMIN_IDS))
async def create_contact_link(client: Client, callback: CallbackQuery):
    me = await client.get_me()
    admin_id = callback.from_user.id
    link = f"https://t.me/{me.username}?start=contact_{admin_id}"

    text = (
        "🔗 **Personal Contact Link**\n\n"
        "Share this link with users. When they click it, they will be connected directly to you via the bot.\n\n"
        f"`{link}`"
    )

    await callback.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back_main")]])
    )


# --- 3. User Management ---
@Client.on_callback_query(filters.regex("^admin_users_menu$") & filters.user(ADMIN_IDS))
async def user_management_menu(client: Client, callback: CallbackQuery):
    text = "👥 **User Management**\n\nWhat would you like to do?"
    buttons = [
        # [InlineKeyboardButton("📜 List All Users", callback_data="admin_users_list")], # Can be huge
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
@Client.on_message(filters.user(ADMIN_IDS) & filters.private, group=5)
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
        await show_admin_dashboard(message)
        return

    # Project Wizard
    if state == "awaiting_project_name":
        db.set_state(user_id, "awaiting_project_desc", {"name": message.text})
        await message.reply_text("✅ Name set. Now enter description.")
        return
    elif state == "awaiting_project_desc":
        db.create_project(data['name'], message.text, user_id)
        db.clear_state(user_id)
        await message.reply_text("🎉 Project created!")
        await show_admin_dashboard(message)
        return

    # Block/Unblock
    elif state == "awaiting_block_id":
        try:
            target = int(message.text)
            db.block_user(target)
            await message.reply_text(f"🚫 User {target} blocked.")
        except:
            await message.reply_text("❌ Invalid ID.")
        db.clear_state(user_id)
        await show_admin_dashboard(message)
        return
    elif state == "awaiting_unblock_id":
        try:
            target = int(message.text)
            db.users.update_one({"user_id": target}, {"$set": {"blocked": False}})
            await message.reply_text(f"✅ User {target} unblocked.")
        except:
            await message.reply_text("❌ Invalid ID.")
        db.clear_state(user_id)
        await show_admin_dashboard(message)
        return

    # Broadcast
    elif state == "awaiting_broadcast":
        # Start Broadcast
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
            # Add delay to avoid flood wait
            if count % 20 == 0:
                await asyncio.sleep(1)

        await status_msg.edit_text(f"✅ Broadcast complete.\nSent: {count}\nFailed: {failed}")
        db.clear_state(user_id)
        await show_admin_dashboard(message)
        return

# --- Back Handler ---
@Client.on_callback_query(filters.regex("^admin_back_main$"))
async def back_to_main_h(client: Client, callback: CallbackQuery):
    await show_admin_dashboard(callback)

@Client.on_callback_query(filters.regex("^admin_close$"))
async def close_panel_h(client: Client, callback: CallbackQuery):
    await callback.message.delete()
