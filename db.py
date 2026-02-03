from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
from config import MONGO_URI

class Database:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client.get_database("xtvfeedback_bot")

        # Collections
        self.projects = self.db.projects
        self.feedback = self.db.feedback
        self.contacts = self.db.contacts
        self.configs = self.db.configs
        self.users = self.db.users  # For FSM states

    # --- Projects ---
    def create_project(self, name, description, feedback_config, expiry_hours, created_by):
        expiry_date = None
        if expiry_hours > 0:
            expiry_date = datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)

        project = {
            "project_name": name,
            "description": description,
            "active": True,
            "feedback_config": feedback_config, # {"stars": bool, "text": bool}
            "expiry_date": expiry_date,
            "created_by": created_by,
            "created_date": datetime.datetime.utcnow(),
            "feedback_count": 0
        }
        return self.projects.insert_one(project).inserted_id

    def get_project(self, project_id_str):
        try:
            return self.projects.find_one({"_id": ObjectId(project_id_str)})
        except:
            return None

    def get_all_projects(self):
        return list(self.projects.find().sort("created_date", -1))

    def get_active_projects(self):
        now = datetime.datetime.utcnow()
        # Active and (no expiry OR expiry > now)
        query = {
            "active": True,
            "$or": [
                {"expiry_date": None},
                {"expiry_date": {"$gt": now}}
            ]
        }
        return list(self.projects.find(query).sort("created_date", -1))

    def toggle_project_active(self, project_id_str, status: bool):
        try:
            self.projects.update_one(
                {"_id": ObjectId(project_id_str)},
                {"$set": {"active": status}}
            )
            return True
        except:
            return False

    def increment_feedback_count(self, project_id):
        self.projects.update_one(
            {"_id": project_id},
            {"$inc": {"feedback_count": 1}}
        )

    # --- Feedback ---
    def add_feedback(self, project_id_str, user_id, rating, text):
        try:
            p_id = ObjectId(project_id_str)
            feedback = {
                "project_id": p_id,
                "user_id": user_id,
                "rating": rating,
                "feedback_text": text,
                "timestamp": datetime.datetime.utcnow()
            }
            self.feedback.insert_one(feedback)
            self.increment_feedback_count(p_id)
            return True
        except Exception as e:
            print(f"Error adding feedback: {e}")
            return False

    def get_feedback_for_project(self, project_id_str):
        try:
            return list(self.feedback.find({"project_id": ObjectId(project_id_str)}))
        except:
            return []

    def get_user_feedback_count(self, user_id):
        return self.feedback.count_documents({"user_id": user_id})

    def get_last_feedback_time(self, user_id):
        last = self.feedback.find_one({"user_id": user_id}, sort=[("timestamp", -1)])
        return last["timestamp"] if last else None

    # --- State Management (FSM) ---
    def set_state(self, user_id, state, data=None):
        if data is None:
            data = {}
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"state": state, "data": data, "updated_at": datetime.datetime.utcnow()}},
            upsert=True
        )

    def get_state(self, user_id):
        return self.users.find_one({"user_id": user_id})

    def clear_state(self, user_id):
        self.users.update_one(
            {"user_id": user_id},
            {"$unset": {"state": "", "data": ""}}
        )

    # --- Configs ---
    def get_config(self, key, default=None):
        doc = self.configs.find_one({"key": key})
        return doc["value"] if doc else default

    def set_config(self, key, value):
        self.configs.update_one(
            {"key": key},
            {"$set": {"value": value}},
            upsert=True
        )

    # --- Contacts ---
    def save_contact_message(self, user_id, message_id_in_channel):
        """
        Maps a message ID in the admin channel to the original user ID.
        We can use this to know who to reply to.
        """
        self.contacts.insert_one({
            "user_id": user_id,
            "channel_message_id": message_id_in_channel,
            "timestamp": datetime.datetime.utcnow(),
            "replied": False
        })

    def get_contact_owner(self, channel_message_id):
        return self.contacts.find_one({"channel_message_id": channel_message_id})

db = Database()
