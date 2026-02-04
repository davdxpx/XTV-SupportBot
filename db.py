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
        self.tickets = self.db.tickets  # Renamed from feedback to tickets for the new system
        self.users = self.db.users
        self.configs = self.db.configs
        # Note: self.contacts is deprecated/merged into tickets logic

    # --- Projects ---
    def create_project(self, name, description, created_by):
        project = {
            "name": name,
            "description": description,
            "active": True,
            "created_by": created_by,
            "created_at": datetime.datetime.utcnow(),
            "ticket_count": 0
        }
        return self.projects.insert_one(project).inserted_id

    def get_project(self, project_id_str):
        try:
            return self.projects.find_one({"_id": ObjectId(project_id_str)})
        except:
            return None

    def get_all_projects(self):
        return list(self.projects.find().sort("created_at", -1))

    def get_active_projects(self):
        return list(self.projects.find({"active": True}).sort("created_at", -1))

    def delete_project(self, project_id_str):
        try:
            self.projects.delete_one({"_id": ObjectId(project_id_str)})
            # We keep tickets for history, but they are now orphaned from the project list
            return True
        except:
            return False

    def increment_ticket_count(self, project_id):
        self.projects.update_one(
            {"_id": project_id},
            {"$inc": {"ticket_count": 1}}
        )

    # --- Tickets (formerly Feedback) ---
    def create_ticket(self, project_id_str, user_id, message_text, message_type="text", file_id=None):
        try:
            p_id = ObjectId(project_id_str)
            ticket = {
                "project_id": p_id,
                "user_id": user_id,
                "message": message_text, # Initial message
                "type": message_type,
                "file_id": file_id,
                "status": "open", # open, closed, in_progress
                "created_at": datetime.datetime.utcnow(),
                "topic_id": None, # ID of the forum topic in admin group
                "history": [] # List of messages in this ticket conversation
            }
            # Add initial message to history
            ticket["history"].append({
                "sender": "user",
                "text": message_text,
                "type": message_type,
                "file_id": file_id,
                "timestamp": datetime.datetime.utcnow()
            })

            t_id = self.tickets.insert_one(ticket).inserted_id
            self.increment_ticket_count(p_id)

            # Update user's current active ticket
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"last_active_project": project_id_str, "last_ticket_id": t_id}},
                upsert=True
            )

            return t_id
        except Exception as e:
            print(f"Error creating ticket: {e}")
            return None

    def add_message_to_ticket(self, ticket_id, sender, text, message_type="text", file_id=None):
        """
        sender: 'user' or 'admin'
        """
        msg = {
            "sender": sender,
            "text": text,
            "type": message_type,
            "file_id": file_id,
            "timestamp": datetime.datetime.utcnow()
        }
        self.tickets.update_one(
            {"_id": ticket_id},
            {
                "$push": {"history": msg},
                "$set": {"updated_at": datetime.datetime.utcnow()}
            }
        )

    def set_ticket_topic(self, ticket_id, topic_id):
        self.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"topic_id": topic_id}}
        )

    def get_ticket(self, ticket_id):
        if isinstance(ticket_id, str):
            ticket_id = ObjectId(ticket_id)
        return self.tickets.find_one({"_id": ticket_id})

    def get_tickets_by_user(self, user_id):
        return list(self.tickets.find({"user_id": user_id}).sort("created_at", -1))

    def get_tickets_by_project(self, project_id_str):
        return list(self.tickets.find({"project_id": ObjectId(project_id_str)}).sort("created_at", -1))

    def get_ticket_by_topic_id(self, topic_id):
        return self.tickets.find_one({"topic_id": topic_id})

    def close_ticket(self, ticket_id):
        self.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"status": "closed", "closed_at": datetime.datetime.utcnow()}}
        )

    # --- Users & State ---
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

    def get_user_topic(self, user_id, project_id_str):
        """Finds an open ticket for this user/project that has a topic assigned."""
        return self.tickets.find_one({
            "user_id": user_id,
            "project_id": ObjectId(project_id_str),
            "topic_id": {"$ne": None},
            "status": {"$ne": "closed"}
        })

    def block_user(self, user_id):
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"blocked": True}},
            upsert=True
        )

    def is_user_blocked(self, user_id):
        u = self.users.find_one({"user_id": user_id})
        return u and u.get("blocked", False)

db = Database()
