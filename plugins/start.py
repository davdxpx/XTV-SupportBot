from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    # Check for deep linking arguments (e.g. /start <project_id>)
    args = message.command
    if len(args) > 1:
        project_id = args[1]
        project = db.get_project(project_id)
        if project and project.get("active"):
            await show_project_welcome(message, project)
            return
        else:
            await message.reply_text("❌ Project not found or inactive.")

    # Show project list
    await show_project_selection(message)

async def show_project_selection(message: Message | CallbackQuery):
    projects = db.get_active_projects()

    if not projects:
        text = "👋 Welcome! currently there are no active projects to give feedback on."
        buttons = None
    else:
        text = "👋 **Welcome!**\n\nPlease select a project to give feedback or get support:"
        buttons_list = []
        for p in projects:
            buttons_list.append([InlineKeyboardButton(p["name"], callback_data=f"user_sel_proj_{p['_id']}")])
        buttons = InlineKeyboardMarkup(buttons_list)

    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=buttons)
    else:
        await message.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^user_sel_proj_"))
async def project_selected(client: Client, callback: CallbackQuery):
    project_id = callback.data.split("_")[-1]
    project = db.get_project(project_id)

    if not project:
        await callback.answer("Project not found!", show_alert=True)
        return

    # We pass the callback.message context to the welcome function
    # But for edit_message_text we need to handle it slightly differently
    text = (
        f"📂 **{project['name']}**\n\n"
        f"{project['description']}\n\n"
        "👇 **How can we help?**\n"
        "Simply send your message, photo, or file here to start a support ticket."
    )

    # Save user state
    db.set_state(callback.from_user.id, "awaiting_feedback", {"project_id": str(project['_id'])})

    await callback.edit_message_text(text)

async def show_project_welcome(message: Message, project):
    text = (
        f"📂 **{project['name']}**\n\n"
        f"{project['description']}\n\n"
        "👇 **How can we help?**\n"
        "Simply send your message, photo, or file here to start a support ticket."
    )
    db.set_state(message.from_user.id, "awaiting_feedback", {"project_id": str(project['_id'])})
    await message.reply_text(text)
