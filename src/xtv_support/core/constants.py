from __future__ import annotations

from enum import IntEnum, StrEnum


class HandlerGroup(IntEnum):
    """Message handler dispatch groups.

    Pyrofork dispatches handlers in ascending group order. Lower runs first.
    """

    MIDDLEWARE_LOG = -2
    MIDDLEWARE_GUARD = -1
    COMMAND = 0
    ADMIN_STATE = 1
    USER_FLOW = 2
    TOPIC = 3
    CATCH_ALL = 99


class UserState(StrEnum):
    """Finite-state-machine identifiers for user interactions."""

    IDLE = ""
    AWAITING_FEEDBACK = "awaiting_feedback"
    AWAITING_CONTACT_MSG = "awaiting_contact_msg"

    # Admin wizards
    AWAITING_PROJECT_NAME = "awaiting_project_name"
    AWAITING_PROJECT_DESC = "awaiting_project_desc"
    AWAITING_PROJECT_TYPE = "awaiting_project_type"
    AWAITING_FEEDBACK_RATING = "awaiting_feedback_rating"
    AWAITING_FEEDBACK_TEXT = "awaiting_feedback_text"
    AWAITING_FEEDBACK_TOPIC = "awaiting_feedback_topic"
    AWAITING_CONTACT_NAME = "awaiting_contact_name"
    AWAITING_BLOCK_ID = "awaiting_block_id"
    AWAITING_UNBLOCK_ID = "awaiting_unblock_id"
    AWAITING_BROADCAST = "awaiting_broadcast"
    AWAITING_TAG_NAME = "awaiting_tag_name"


class CallbackPrefix(StrEnum):
    """Prefixes for inline-button callback_data."""

    # User-facing
    USER_SELECT_PROJECT = "u:sp"
    USER_RATE = "u:rate"
    USER_TICKETS_LIST = "u:tks"
    USER_TICKETS_VIEW = "u:tkv"
    USER_TICKETS_CLOSE = "u:tkc"
    USER_LANG_PICK = "u:lang"

    # KB gate (Phase 6c)
    USER_KB_HELPFUL = "u:kbh"
    USER_KB_NOT_HELPFUL = "u:kbn"
    USER_KB_HUMAN = "u:kbm"

    # Admin dashboard
    ADMIN_HOME = "a:home"
    ADMIN_CLOSE = "a:close"
    ADMIN_PROJECTS = "a:projects"
    ADMIN_PROJECT_VIEW = "a:pv"
    ADMIN_PROJECT_DELETE = "a:pd"
    ADMIN_PROJECT_TICKETS = "a:pt"
    ADMIN_PROJECT_CREATE = "a:pc"
    ADMIN_PROJECT_TYPE = "a:ptype"
    ADMIN_PROJECT_RATING = "a:prating"
    ADMIN_PROJECT_TEXT = "a:ptext"

    ADMIN_CONTACT_START = "a:cstart"
    ADMIN_CONTACT_ANON = "a:canon"

    ADMIN_USERS = "a:users"
    ADMIN_USERS_BLOCK = "a:ublock"
    ADMIN_USERS_UNBLOCK = "a:uunblock"

    ADMIN_BROADCAST_START = "a:bstart"
    ADMIN_BROADCAST_CONFIRM = "a:bconf"
    ADMIN_BROADCAST_PAUSE = "a:bpause"
    ADMIN_BROADCAST_RESUME = "a:bresume"
    ADMIN_BROADCAST_CANCEL = "a:bcancel"

    ADMIN_TAGS = "a:tags"
    ADMIN_TAG_NEW = "a:tnew"
    ADMIN_TAG_DEL = "a:tdel"

    # Ticket header actions
    TICKET_ASSIGN = "t:assign"
    TICKET_ASSIGN_PICK = "t:apick"
    TICKET_TAG = "t:tag"
    TICKET_TAG_TOGGLE = "t:tt"
    TICKET_PRIORITY = "t:prio"
    TICKET_PRIORITY_PICK = "t:ppick"
    TICKET_CLOSE = "t:close"


DEFAULT_PROGRESS_WIDTH = 10
MAX_PROJECT_NAME_LEN = 64
MAX_PROJECT_DESC_LEN = 512
MAX_BROADCAST_LEN = 4000
TAG_NAME_REGEX = r"^[a-z0-9_-]{1,24}$"

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
