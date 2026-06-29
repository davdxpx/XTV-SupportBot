"""External User Directory Domain Models.

This module contains the primary dataclasses and protocols required for the External User
Directory feature, including enumerations and signal abstractions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class FieldKind(StrEnum):
    """How to interpret the external field's data."""

    BOOLEAN = "boolean"
    ENUM = "enum"
    NUMERIC_THRESHOLD = "numeric_threshold"


KNOWN_LOCAL_FIELDS = (
    "vip_status",
    "tier_label",
    "priority_score",
    "display_badge",
)
"""The fixed catalogue of internal canonical names we use elsewhere in SupportBot.
- ``vip_status``: indicates if the user is considered a VIP.
- ``tier_label``: textual label for the user's tier.
- ``priority_score``: a numeric score used for routing priority.
- ``display_badge``: visual badge shown in UI surfaces.
"""


@dataclass(frozen=True, slots=True)
class EnumRankMapping:
    """Maps raw string values found in the external DB to an ordered rank."""

    raw_value: str
    rank_label: str
    rank_order: int
    is_vip: bool


@dataclass(frozen=True, slots=True)
class FieldMapping:
    """Describes ONE external field and how to interpret it."""

    local_name: str
    external_field_path: str
    kind: FieldKind
    enum_mapping: tuple[EnumRankMapping, ...] = ()
    numeric_vip_threshold: float | None = None
    numeric_max_for_scale: float | None = None
    boolean_true_means_vip: bool = True


@dataclass(frozen=True, slots=True)
class ExternalDirectoryConfig:
    """The full, persisted configuration for one operator's external DB."""

    enabled: bool
    connection_uri_ref: str
    database_name: str
    collection_name: str
    external_id_field: str
    external_id_is_string: bool = False
    expiry_field_path: str | None = None
    field_mappings: tuple[FieldMapping, ...] = ()
    last_verified_at: datetime | None = None
    last_verification_error: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedUserSignal:
    """The OUTPUT of interpreting one external document against a config."""

    is_vip: bool = False
    tier_label: str | None = None
    tier_rank_order: int = 0
    priority_score: float | None = None
    display_badge: str | None = None
    source: str = "none"


class DirectoryProviderLike(Protocol):
    """Protocol for fetching a user's directory signal."""

    async def get_signal(self, telegram_user_id: int) -> ResolvedUserSignal: ...
