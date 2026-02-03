from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import ADMIN_IDS
from db import db
import io
import csv
from plugins.admin import show_admin_menu # Import the menu function

# Re-define constants or import them if I shared them.
# Better to just use strings or define here.
STATE_CONFIG_WELCOME = "conf_welcome"
STATE_CONFIG_MAX_FB = "conf_max_fb"

def is_admin(_, __, message: Message):
    return message.from_user.id in ADMIN_IDS

admin_filter = filters.create(is_admin)

@Client.on_callback_query(filters.regex("^admin_view_proj_"))
async def admin_view_project(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_view_proj_", "")
    project = db.get_project(project_id_str)

    if not project:
        await callback.answer("Project not found.", show_alert=True)
        await show_admin_menu(callback.message)
        return

    status = "Active" if project["active"] else "Inactive"
    text = (
        f"**Project Details**\n\n"
        f"**Name:** {project['project_name']}\n"
        f"**Description:** {project['description']}\n"
        f"**Status:** {status}\n"
        f"**Created:** {project['created_date']}\n"
        f"**Feedback Count:** {project['feedback_count']}\n"
        f"**Link:** https://t.me/{(await client.get_me()).username}?start=project_{project_id_str}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Toggle Active ({'Disable' if project['active'] else 'Enable'})", callback_data=f"admin_toggle_proj_{project_id_str}")],
        [InlineKeyboardButton("📥 Export Feedback (CSV)", callback_data=f"admin_export_proj_{project_id_str}")],
        [InlineKeyboardButton("Back to List", callback_data="admin_list_projects")]
    ])

    await callback.message.edit_message_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@Client.on_callback_query(filters.regex("^admin_toggle_proj_"))
async def admin_toggle_project(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_toggle_proj_", "")
    project = db.get_project(project_id_str)

    if project:
        new_status = not project["active"]
        db.toggle_project_active(project_id_str, new_status)
        await callback.answer(f"Project marked as {'Active' if new_status else 'Inactive'}.")

        callback.data = f"admin_view_proj_{project_id_str}"
        await admin_view_project(client, callback)
    else:
        await callback.answer("Error updating project.", show_alert=True)

@Client.on_callback_query(filters.regex("^admin_export_proj_"))
async def admin_export_feedback(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_export_proj_", "")
    project = db.get_project(project_id_str)
    feedbacks = db.get_feedback_for_project(project_id_str)

    if not feedbacks:
        await callback.answer("No feedback found for this project.", show_alert=True)
        return

    await callback.answer("Generating CSV...", show_alert=False)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "User ID", "Rating", "Feedback Text"])

    for fb in feedbacks:
        writer.writerow([
            fb.get("timestamp", ""),
            fb.get("user_id", ""),
            fb.get("rating", "N/A"),
            fb.get("feedback_text", "")
        ])

    output.seek(0)

    await client.send_document(
        chat_id=callback.message.chat.id,
        document=io.BytesIO(output.getvalue().encode()),
        file_name=f"feedback_{project['project_name']}.csv",
        caption=f"Feedback export for **{project['project_name']}**"
    )

async def show_config_menu(message):
    welcome_msg = db.get_config("welcome_message", "Welcome!")
    max_fb = db.get_config("max_feedback_per_user", 5)

    text = (
        f"**Bot Configuration**\n\n"
        f"**Max Feedback per User:** {max_fb}\n"
        f"**Welcome Message:** {welcome_msg}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Edit Max Feedback", callback_data="admin_edit_conf_max")],
        [InlineKeyboardButton("Edit Welcome Message", callback_data="admin_edit_conf_welcome")],
        [InlineKeyboardButton("Back", callback_data="admin_menu")]
    ])

    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=keyboard)
    else:
        await message.edit_message_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^admin_edit_conf_"))
async def admin_edit_config(client, callback: CallbackQuery):
    action = callback.data
    user_id = callback.from_user.id

    if action == "admin_edit_conf_max":
        db.set_state(user_id, STATE_CONFIG_MAX_FB)
        await callback.message.edit_message_text(
            "Enter the new maximum number of feedbacks per user:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )
    elif action == "admin_edit_conf_welcome":
        db.set_state(user_id, STATE_CONFIG_WELCOME)
        await callback.message.edit_message_text(
            "Enter the new Welcome Message:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )

@Client.on_message(filters.text & admin_filter)
async def admin_config_text_handler(client, message: Message):
    user_id = message.from_user.id
    user_state = db.get_state(user_id)

    if not user_state:
        message.continue_propagation()
        return

    state = user_state.get("state")

    if state == STATE_CONFIG_MAX_FB:
        try:
            val = int(message.text)
            db.set_config("max_feedback_per_user", val)
            await message.reply_text("✅ Max feedback limit updated.")
            db.clear_state(user_id)
            await show_config_menu(message)
        except ValueError:
            await message.reply_text("Please enter a valid integer.")

    elif state == STATE_CONFIG_WELCOME:
        db.set_config("welcome_message", message.text)
        await message.reply_text("✅ Welcome message updated.")
        db.clear_state(user_id)
        await show_config_menu(message)
    else:
        message.continue_propagation()
