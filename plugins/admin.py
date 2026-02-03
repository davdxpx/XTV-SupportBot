from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import ADMIN_IDS
from db import db
import asyncio
import io
import csv
from bson.objectid import ObjectId

# States for Project Creation
STATE_PROJECT_NAME = "proj_name"
STATE_PROJECT_DESC = "proj_desc"
STATE_PROJECT_CONFIG_STARS = "proj_conf_stars"
STATE_PROJECT_CONFIG_TEXT = "proj_conf_text"
STATE_PROJECT_EXPIRY = "proj_expiry"

# States for Configs
STATE_CONFIG_WELCOME = "conf_welcome"
STATE_CONFIG_MAX_FB = "conf_max_fb"

def is_admin(_, __, message: Message):
    return message.from_user.id in ADMIN_IDS

admin_filter = filters.create(is_admin)

@Client.on_message(filters.command("admin") & admin_filter)
async def admin_panel(client, message):
    await show_admin_menu(message)

async def show_admin_menu(message_or_callback):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Project", callback_data="admin_create_project")],
        [InlineKeyboardButton("📋 List Projects", callback_data="admin_list_projects")],
        [InlineKeyboardButton("⚙️ Configs", callback_data="admin_configs")],
    ])
    text = "**Admin Panel**\nSelect an option:"

    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard)
    else:
        # Check if message is editable (not media caption usually, but here it's text)
        try:
            await message_or_callback.edit_text(text, reply_markup=keyboard)
        except AttributeError:
             await message_or_callback.message.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex("^admin_") & ~filters.regex("^admin_proj_") & ~filters.regex("^admin_cancel") & ~filters.regex("^admin_view_") & ~filters.regex("^admin_toggle_") & ~filters.regex("^admin_export_") & ~filters.regex("^admin_edit_conf_"))
async def admin_callbacks(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        return

    data = callback.data
    if data == "admin_menu":
        db.clear_state(user_id)
        await show_admin_menu(callback.message)

    elif data == "admin_create_project":
        db.set_state(user_id, STATE_PROJECT_NAME)
        await callback.message.edit_text(
            "**Create New Project**\n\nEnter the **Project Name**:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )

    elif data == "admin_list_projects":
        projects = db.get_all_projects()
        if not projects:
            await callback.answer("No projects found.", show_alert=True)
            return

        buttons = []
        for p in projects:
            status = "🟢" if p["active"] else "🔴"
            buttons.append([InlineKeyboardButton(f"{status} {p['project_name']} ({p['feedback_count']})", callback_data=f"admin_view_proj_{p['_id']}")])

        buttons.append([InlineKeyboardButton("Back", callback_data="admin_menu")])
        await callback.message.edit_text("**Project List**", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin_configs":
        await show_config_menu(callback.message)

@Client.on_callback_query(filters.regex("^admin_cancel"))
async def admin_cancel(client, callback: CallbackQuery):
    db.clear_state(callback.from_user.id)
    await show_admin_menu(callback.message)

@Client.on_message(filters.text & admin_filter)
async def admin_fsm_text(client, message: Message):
    user_id = message.from_user.id
    user_state = db.get_state(user_id)

    if not user_state:
        message.continue_propagation()
        return

    state = user_state.get("state")
    data = user_state.get("data", {})

    # --- Project Creation ---
    if state == STATE_PROJECT_NAME:
        db.set_state(user_id, STATE_PROJECT_DESC, {**data, "name": message.text})
        await message.reply_text(
            f"Name: **{message.text}**\n\nNow enter the **Project Description**:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )

    elif state == STATE_PROJECT_DESC:
        db.set_state(user_id, STATE_PROJECT_CONFIG_STARS, {**data, "desc": message.text})
        await message.reply_text(
            f"Description saved.\n\n**Enable Star Ratings (1-5)?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes", callback_data="admin_proj_stars_yes"),
                 InlineKeyboardButton("No", callback_data="admin_proj_stars_no")],
                [InlineKeyboardButton("Cancel", callback_data="admin_cancel")]
            ])
        )

    elif state == STATE_PROJECT_EXPIRY:
        try:
            hours = int(message.text)
            if hours < 0:
                raise ValueError
        except ValueError:
            await message.reply_text("Please enter a valid non-negative integer (0 for infinite).")
            return

        # Create Project
        feedback_config = {
            "stars": data.get("stars"),
            "text": data.get("text_feedback")
        }

        project_id = db.create_project(
            name=data.get("name"),
            description=data.get("desc"),
            feedback_config=feedback_config,
            expiry_hours=hours,
            created_by=user_id
        )

        db.clear_state(user_id)

        bot_username = (await client.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start=project_{project_id}"

        await message.reply_text(
            f"✅ **Project Created Successfully!**\n\n"
            f"**Name:** {data.get('name')}\n"
            f"**Link:** {deep_link}\n\n"
            f"Users can now send feedback via this link.",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="admin_menu")]])
        )

    # --- Config Editing ---
    elif state == STATE_CONFIG_MAX_FB:
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

@Client.on_callback_query(filters.regex("^admin_proj_"))
async def admin_fsm_callbacks(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_state = db.get_state(user_id)

    if not user_state:
        await callback.answer("Session expired.", show_alert=True)
        await show_admin_menu(callback.message)
        return

    state = user_state.get("state")
    data = user_state.get("data", {})
    action = callback.data

    if state == STATE_PROJECT_CONFIG_STARS:
        stars_enabled = (action == "admin_proj_stars_yes")
        db.set_state(user_id, STATE_PROJECT_CONFIG_TEXT, {**data, "stars": stars_enabled})
        await callback.message.edit_text(
            f"Stars: {'Enabled' if stars_enabled else 'Disabled'}\n\n**Enable Text Feedback?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes", callback_data="admin_proj_text_yes"),
                 InlineKeyboardButton("No", callback_data="admin_proj_text_no")],
                [InlineKeyboardButton("Cancel", callback_data="admin_cancel")]
            ])
        )

    elif state == STATE_PROJECT_CONFIG_TEXT:
        text_enabled = (action == "admin_proj_text_yes")

        # Check if at least one is enabled
        if not data.get("stars") and not text_enabled:
            await callback.answer("You must enable at least one feedback type (Stars or Text).", show_alert=True)
            return

        db.set_state(user_id, STATE_PROJECT_EXPIRY, {**data, "text_feedback": text_enabled})
        await callback.message.edit_text(
            f"Text: {'Enabled' if text_enabled else 'Disabled'}\n\n**Enter Expiry Time in Hours** (0 for infinite):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )

# --- Consolidated Admin Extras ---

@Client.on_callback_query(filters.regex("^admin_view_proj_"))
async def admin_view_project(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_view_proj_", "")
    project = db.get_project(project_id_str)

    if not project:
        await callback.answer("Project not found.", show_alert=True)
        await show_admin_menu(callback.message)
        return

    status = "Active" if project["active"] else "Inactive"
    created = project.get("created_date", "Unknown").strftime("%Y-%m-%d %H:%M") if project.get("created_date") else "Unknown"

    text = (
        f"**Project Details**\n\n"
        f"**Name:** {project['project_name']}\n"
        f"**Description:** {project['description']}\n"
        f"**Status:** {status}\n"
        f"**Created:** {created}\n"
        f"**Feedback Count:** {project['feedback_count']}\n"
        f"**Link:** https://t.me/{(await client.get_me()).username}?start=project_{project_id_str}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Toggle Active ({'Disable' if project['active'] else 'Enable'})", callback_data=f"admin_toggle_proj_{project_id_str}")],
        [InlineKeyboardButton("📥 Export Feedback (CSV)", callback_data=f"admin_export_proj_{project_id_str}")],
        [InlineKeyboardButton("🗑️ Delete Project", callback_data=f"admin_delete_proj_confirm_{project_id_str}")],
        [InlineKeyboardButton("Back to List", callback_data="admin_list_projects")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

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

@Client.on_callback_query(filters.regex("^admin_delete_proj_confirm_"))
async def admin_delete_project_confirm(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_delete_proj_confirm_", "")

    await callback.message.edit_text(
        "**Are you sure you want to delete this project?**\nThis action cannot be undone.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, Delete", callback_data=f"admin_delete_proj_do_{project_id_str}")],
            [InlineKeyboardButton("Cancel", callback_data=f"admin_view_proj_{project_id_str}")]
        ])
    )

@Client.on_callback_query(filters.regex("^admin_delete_proj_do_"))
async def admin_delete_project_do(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("admin_delete_proj_do_", "")

    # We should probably hard delete or soft delete. Let's do hard delete for now or update a "deleted" flag.
    # Given requirements didn't specify, I will update a 'deleted' flag if I want to be safe, but DB method says "toggle active".
    # I'll implement a delete method in DB.

    # For now, let's assume we implement a delete method.
    if db.delete_project(project_id_str):
        await callback.answer("Project deleted.")
        # Go back to list
        callback.data = "admin_list_projects"
        await admin_callbacks(client, callback)
    else:
        await callback.answer("Error deleting project.", show_alert=True)

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

async def show_config_menu(message_or_callback):
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

    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.edit_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^admin_edit_conf_"))
async def admin_edit_config(client, callback: CallbackQuery):
    action = callback.data
    user_id = callback.from_user.id

    if action == "admin_edit_conf_max":
        db.set_state(user_id, STATE_CONFIG_MAX_FB)
        await callback.message.edit_text(
            "Enter the new maximum number of feedbacks per user:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )
    elif action == "admin_edit_conf_welcome":
        db.set_state(user_id, STATE_CONFIG_WELCOME)
        await callback.message.edit_text(
            "Enter the new Welcome Message:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )
