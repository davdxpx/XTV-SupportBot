from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from bson import ObjectId

TicketStatus = Literal["open", "closed"]
TicketType = Literal["text", "photo", "document"]
ProjectType = Literal["support", "feedback"]
Priority = Literal["low", "normal", "high"]
BroadcastState = Literal["queued", "running", "paused", "done", "cancelled"]


class HistoryEntry(TypedDict, total=False):
    sender: Literal["user", "admin", "system"]
    text: str
    type: TicketType
    file_id: str | None
    timestamp: datetime


class TicketDoc(TypedDict, total=False):
    _id: ObjectId
    project_id: ObjectId | None
    user_id: int
    contact_uuid: str | None
    message: str
    type: TicketType
    file_id: str | None
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    closed_by: int | None
    close_reason: str | None
    topic_id: int | None
    topic_fallback: bool
    header_msg_id: int | None
    history: list[HistoryEntry]
    assignee_id: int | None
    assigned_at: datetime | None
    assigned_by: int | None
    tags: list[str]
    priority: Priority
    sla_deadline: datetime | None
    sla_warned: bool
    last_user_msg_at: datetime
    last_admin_msg_at: datetime | None


class ProjectDoc(TypedDict, total=False):
    _id: ObjectId
    name: str
    description: str
    type: ProjectType
    feedback_topic_id: int | None
    has_rating: bool
    has_text: bool
    active: bool
    created_by: int
    created_at: datetime
    ticket_count: int


class UserDoc(TypedDict, total=False):
    user_id: int
    first_name: str
    username: str | None
    last_seen: datetime
    state: str
    data: dict
    last_active_project: str | None
    last_ticket_id: ObjectId | None
    blocked: bool
    cooldown_until: datetime | None
    flood_score: int
    lang: str
    notified_on_assign: bool


class ContactLinkDoc(TypedDict, total=False):
    uuid: str
    admin_id: int
    display_name: str
    is_anonymous: bool
    created_at: datetime


class TagDoc(TypedDict, total=False):
    _id: ObjectId
    name: str
    emoji: str
    description: str
    created_by: int
    created_at: datetime


class BroadcastDoc(TypedDict, total=False):
    _id: ObjectId
    admin_id: int
    text: str
    state: BroadcastState
    total: int
    sent: int
    failed: int
    blocked_count: int
    started_at: datetime
    finished_at: datetime | None
    progress_chat_id: int | None
    progress_msg_id: int | None


class AuditDoc(TypedDict, total=False):
    actor_id: int
    action: str
    target_type: str
    target_id: str
    payload: dict
    ts: datetime

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
