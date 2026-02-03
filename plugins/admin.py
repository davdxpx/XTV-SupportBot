from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import ADMIN_IDS
from db import db
import asyncio
import io
import csv
from bson.objectid import ObjectId

# States
STATE_PROJECT_NAME = "proj_name"
STATE_PROJECT_DESC = "proj_desc"
STATE_PROJECT_CONFIG_STARS = "proj_conf_stars"
STATE_PROJECT_CONFIG_TEXT = "proj_conf_text"
STATE_PROJECT_EXPIRY = "proj_expiry"

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
        await message_or_callback.edit_message_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^admin_") & ~filters.regex("^admin_proj_") & ~filters.regex("^admin_cancel"))
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
        await callback.message.edit_message_text(
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
        await callback.message.edit_message_text("**Project List**", reply_markup=InlineKeyboardMarkup(buttons))

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
        await callback.message.edit_message_text(
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
        await callback.message.edit_message_text(
            f"Text: {'Enabled' if text_enabled else 'Disabled'}\n\n**Enter Expiry Time in Hours** (0 for infinite):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_cancel")]])
        )
