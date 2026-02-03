from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
from bson.objectid import ObjectId
import datetime

# States
STATE_FEEDBACK_RATING = "user_fb_rating"
STATE_FEEDBACK_TEXT = "user_fb_text"

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    text = (
        "**XTV Feedback Bot Help**\n\n"
        "Here is how to use this bot:\n"
        "🔹 **/start** - List active projects to give feedback on.\n"
        "🔹 **/contact** - Send an anonymous message to the admin.\n"
        "🔹 **/help** - Show this help message.\n\n"
        "If you are an admin, use **/admin** to manage projects."
    )
    await message.reply_text(text)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    args = message.command
    user_id = message.from_user.id

    # Check if deep link
    if len(args) > 1:
        param = args[1]
        if param.startswith("project_"):
            project_id_str = param.replace("project_", "")
            await start_feedback_flow(client, message.chat.id, user_id, project_id_str)
            return

    # No deep link: List active projects
    projects = db.get_active_projects()
    if not projects:
        await message.reply_text("No active projects for feedback at the moment.")
        return

    buttons = []
    for p in projects:
        buttons.append([InlineKeyboardButton(p["project_name"], callback_data=f"user_start_proj_{p['_id']}")])

    await message.reply_text(
        "**What do you want to give feedback on?**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^user_start_proj_"))
async def user_select_project(client, callback: CallbackQuery):
    project_id_str = callback.data.replace("user_start_proj_", "")
    await start_feedback_flow(client, callback.message.chat.id, callback.from_user.id, project_id_str)
    await callback.answer()

async def start_feedback_flow(client, chat_id, user_id, project_id_str):
    project = db.get_project(project_id_str)
    if not project:
        await client.send_message(chat_id, "Project not found or invalid.")
        return

    # Check if active/expired
    if not project.get("active"):
         await client.send_message(chat_id, "This project is no longer accepting feedback.")
         return

    # Check expiry
    if project.get("expiry_date"):
        # This should have been handled by get_active_projects but direct link might bypass
        if project["expiry_date"] < datetime.datetime.utcnow():
             await client.send_message(chat_id, "This project has expired.")
             return

    # Check max feedback limit
    max_fb = int(db.get_config("max_feedback_per_user", 5))
    user_fb_count = db.get_user_feedback_count(user_id)
    if user_fb_count >= max_fb:
         await client.send_message(chat_id, f"You have reached the maximum limit of {max_fb} feedbacks.")
         return

    # Check cooldown (1 minute)
    last_time = db.get_last_feedback_time(user_id)
    if last_time:
        diff = (datetime.datetime.utcnow() - last_time).total_seconds()
        if diff < 60:
            await client.send_message(chat_id, "Please wait a minute before sending another feedback.")
            return

    config = project.get("feedback_config", {})
    stars_enabled = config.get("stars", False)
    text_enabled = config.get("text", False)

    data = {
        "project_id": project_id_str,
        "stars_enabled": stars_enabled,
        "text_enabled": text_enabled,
        "project_name": project["project_name"]
    }

    # Show project description before starting feedback
    desc = project.get("description", "")
    msg_text = f"**Feedback for {project['project_name']}**\n"
    if desc:
        msg_text += f"_{desc}_\n"
    msg_text += "\n"

    if stars_enabled:
        db.set_state(user_id, STATE_FEEDBACK_RATING, data)
        msg_text += "Please rate your experience:"
        await client.send_message(
            chat_id,
            msg_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("1 ⭐️", callback_data="rate_1"),
                    InlineKeyboardButton("2 ⭐️", callback_data="rate_2"),
                    InlineKeyboardButton("3 ⭐️", callback_data="rate_3"),
                    InlineKeyboardButton("4 ⭐️", callback_data="rate_4"),
                    InlineKeyboardButton("5 ⭐️", callback_data="rate_5")
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="user_cancel")]
            ])
        )
    elif text_enabled:
        db.set_state(user_id, STATE_FEEDBACK_TEXT, data)
        msg_text += "Please write your feedback below:"
        await client.send_message(
            chat_id,
            msg_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="user_cancel")]])
        )
    else:
        await client.send_message(chat_id, "This project has no feedback methods configured.")

@Client.on_callback_query(filters.regex("^rate_"))
async def user_rating_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_state = db.get_state(user_id)

    if not user_state or user_state.get("state") != STATE_FEEDBACK_RATING:
        await callback.answer("Session expired or invalid.", show_alert=True)
        return

    rating = int(callback.data.replace("rate_", ""))
    data = user_state.get("data", {})
    data["rating"] = rating

    if data.get("text_enabled"):
        db.set_state(user_id, STATE_FEEDBACK_TEXT, data)
        # Use edit_text
        try:
             await callback.message.edit_text(
                f"Rated: {rating} ⭐️\n\nNow please write your feedback text:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="user_cancel")]])
            )
        except AttributeError:
             pass # callback.message should be valid if edit_text fails with attribute error

    else:
        # Finish
        await submit_feedback(client, user_id, data)
        await callback.message.edit_text(
            f"Rated: {rating} ⭐️\n\nThank you for your feedback!",
        )
        db.clear_state(user_id)

    await callback.answer()

@Client.on_message(filters.text & filters.private & ~filters.command("start") & ~filters.command("admin") & ~filters.command("contact"))
async def user_fsm_text(client, message: Message):
    user_id = message.from_user.id
    user_state = db.get_state(user_id)

    if not user_state:
        message.continue_propagation()
        return

    state = user_state.get("state")
    data = user_state.get("data", {})

    if state == STATE_FEEDBACK_TEXT:
        feedback_text = message.text
        data["feedback_text"] = feedback_text

        await submit_feedback(client, user_id, data)

        await message.reply_text("Thank you for your feedback!")
        db.clear_state(user_id)
    else:
        message.continue_propagation()

@Client.on_callback_query(filters.regex("^user_cancel"))
async def user_cancel(client, callback: CallbackQuery):
    db.clear_state(callback.from_user.id)
    await callback.message.edit_text("❌ Feedback cancelled.")
    await callback.answer()

async def submit_feedback(client, user_id, data):
    project_id = data.get("project_id")
    rating = data.get("rating") # None if not enabled
    text = data.get("feedback_text") # None if not enabled
    project_name = data.get("project_name", "Unknown Project")

    db.add_feedback(project_id, user_id, rating, text)

    # Notify Admin
    from config import ADMIN_CHANNEL_ID

    msg = (
        f"📝 **New Feedback Received**\n\n"
        f"**Project:** {project_name}\n"
        f"**User:** `{user_id}`\n"
    )
    if rating:
        msg += f"**Rating:** {rating} ⭐️\n"
    if text:
        msg += f"**Feedback:**\n{text}"

    try:
        await client.send_message(ADMIN_CHANNEL_ID, msg)
    except Exception as e:
        print(f"Failed to send feedback notification: {e}")
