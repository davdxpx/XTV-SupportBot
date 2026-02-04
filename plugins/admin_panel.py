from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from config import ADMIN_IDS

# --- Admin Panel Command ---
@Client.on_message(filters.command("panel") & filters.user(ADMIN_IDS) & filters.private)
async def admin_panel(client: Client, message: Message):
    await show_admin_panel(message)

async def show_admin_panel(message: Message | CallbackQuery):
    text = "🛠 **Admin Panel**\n\nManage your projects and support tickets here."
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Manage Projects", callback_data="admin_projects")],
        # [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")], # Future idea
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ])

    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=buttons)
    else:
        await message.edit_message_text(text, reply_markup=buttons)

# --- Project Management Menu ---
@Client.on_callback_query(filters.regex("^admin_projects$") & filters.user(ADMIN_IDS))
async def manage_projects_menu(client: Client, callback: CallbackQuery):
    projects = db.get_all_projects()

    text = f"📂 **Projects ({len(projects)})**\n\nSelect a project or create a new one."

    buttons_list = []
    for p in projects:
        status = "🟢" if p.get("active") else "🔴"
        buttons_list.append([InlineKeyboardButton(f"{status} {p['name']}", callback_data=f"admin_proj_view_{p['_id']}")])

    buttons_list.append([InlineKeyboardButton("➕ Create New Project", callback_data="admin_proj_create")])
    buttons_list.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back_main")])

    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons_list))

# --- Create Project Wizard ---
@Client.on_callback_query(filters.regex("^admin_proj_create$") & filters.user(ADMIN_IDS))
async def create_project_start(client: Client, callback: CallbackQuery):
    await callback.message.delete()
    msg = await callback.message.reply_text(
        "📝 **Create New Project**\n\nPlease enter the **name** of the project.\n\nType /cancel to abort."
    )
    db.set_state(callback.from_user.id, "awaiting_project_name", {"msg_id": msg.id})

@Client.on_message(filters.user(ADMIN_IDS) & filters.private, group=1)
async def handle_admin_input(client: Client, message: Message):
    user_id = message.from_user.id
    state_doc = db.get_state(user_id)

    if not state_doc or "state" not in state_doc:
        return

    state = state_doc["state"]
    data = state_doc.get("data", {})

    if message.text == "/cancel":
        db.clear_state(user_id)
        await message.reply_text("❌ Action cancelled.")
        await show_admin_panel(message)
        return

    if state == "awaiting_project_name":
        project_name = message.text
        db.set_state(user_id, "awaiting_project_desc", {"name": project_name})
        await message.reply_text(
            f"✅ Name: **{project_name}**\n\nNow enter a short **description** for this project."
        )

    elif state == "awaiting_project_desc":
        desc = message.text
        name = data.get("name")

        # Create Project
        new_id = db.create_project(name, desc, user_id)
        db.clear_state(user_id)

        await message.reply_text(
            f"🎉 **Project Created!**\n\nName: {name}\nID: `{new_id}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_projects")]])
        )

# --- View Project ---
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
        f"Active: {'✅' if project.get('active') else '❌'}\n"
        f"ID: `{project['_id']}`"
    )

    buttons = [
        [InlineKeyboardButton("📜 Show Feedbacks", callback_data=f"admin_proj_feedbacks_{project_id}")],
        [InlineKeyboardButton("🗑 Delete Project", callback_data=f"admin_proj_delete_{project_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_projects")]
    ]

    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Delete Project ---
@Client.on_callback_query(filters.regex("^admin_proj_delete_") & filters.user(ADMIN_IDS))
async def delete_project(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    if db.delete_project(project_id):
        await callback.answer("Project deleted!", show_alert=True)
        await manage_projects_menu(client, callback)
    else:
        await callback.answer("Error deleting project.", show_alert=True)

# --- Show Feedbacks (Placeholder for now) ---
@Client.on_callback_query(filters.regex("^admin_proj_feedbacks_") & filters.user(ADMIN_IDS))
async def show_feedbacks_list(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    tickets = db.get_tickets_by_project(project_id)

    if not tickets:
        await callback.answer("No tickets found for this project.", show_alert=True)
        return

    text = f"📜 **Recent Tickets**\n\n"
    for t in tickets[:10]: # Limit to 10
        status = "🟢" if t['status'] == 'open' else "🔴"
        text += f"{status} `{str(t['_id'])[-4:]}`: {t['message'][:30]}...\n"

    await callback.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"admin_proj_view_{project_id}")]])
    )

# --- Back Handlers ---
@Client.on_callback_query(filters.regex("^admin_back_main$"))
async def back_to_main(client: Client, callback: CallbackQuery):
    await show_admin_panel(callback)

@Client.on_callback_query(filters.regex("^admin_close$"))
async def close_panel(client: Client, callback: CallbackQuery):
    await callback.message.delete()
