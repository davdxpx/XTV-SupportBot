from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import db
import datetime

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    # Ensure user is in DB
    db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "first_name": message.from_user.first_name,
            "username": message.from_user.username,
            "last_seen": datetime.datetime.utcnow()
        }},
        upsert=True
    )

    # Check for deep linking arguments
    args = message.command
    if len(args) > 1:
        payload = args[1]

        # 1. Contact Link (contact_<uuid>)
        if payload.startswith("contact_"):
            try:
                uuid_str = payload.replace("contact_", "")
                link_doc = db.get_contact_link(uuid_str)

                if link_doc:
                    await start_contact_session(client, message, link_doc)
                    return
                else:
                    await message.reply_text("❌ Contact link invalid or expired.")
            except Exception as e:
                print(f"Error parsing contact link: {e}")
                pass

        # 2. Project ID (Direct Project Link)
        project = db.get_project(payload)
        if project and project.get("active"):
            await show_project_welcome(message, project)
            return
        elif not payload.startswith("contact_"):
             await message.reply_text("❌ Project not found or inactive.")

    # Show project list
    await show_project_selection(message)

async def start_contact_session(client: Client, message: Message, link_doc: dict):
    # Retrieve Admin Info (optional, for display)
    admin_id = link_doc.get("admin_id")
    display_name = link_doc.get("display_name", "Support Agent")
    is_anon = link_doc.get("is_anonymous", False)

    if not is_anon:
        try:
            admin_user = await client.get_users(admin_id)
            display_name = admin_user.first_name
        except:
            pass

    text = (
        f"📞 **Direct Contact**\n\n"
        f"You are now connected with **{display_name}**.\n"
        "Send a message here to start a private conversation."
    )

    # We set a special state
    db.set_state(message.from_user.id, "awaiting_contact_msg", {"contact_uuid": link_doc["uuid"]})
    await message.reply_text(text)

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
