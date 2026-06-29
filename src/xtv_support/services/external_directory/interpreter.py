"""External User Directory Interpreter.

A pure-function interpreter that resolves a raw user document into a standardized signal.
"""
from __future__ import annotations

import datetime
from typing import Any

from xtv_support.core.logger import get_logger
from xtv_support.services.external_directory.model import (
    ExternalDirectoryConfig,
    FieldKind,
    ResolvedUserSignal,
)
from xtv_support.services.rules.model import _walk as walk_doc
from xtv_support.utils.time import parse_iso

log = get_logger("external_directory.interpreter")


def _parse_expiry(value: Any) -> datetime.datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
        except (ValueError, TypeError, OSError):
            return None
    if isinstance(value, str):
        return parse_iso(value)
    return None


def resolve_signal(
    raw_doc: dict[str, Any] | None,
    config: ExternalDirectoryConfig,
    *,
    now: datetime.datetime | None = None,
) -> ResolvedUserSignal:
    if raw_doc is None:
        return ResolvedUserSignal()

    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)

    if config.expiry_field_path:
        expiry_val = walk_doc(raw_doc, config.expiry_field_path)
        expiry_dt = _parse_expiry(expiry_val)
        if expiry_dt is not None and expiry_dt < now:
            return ResolvedUserSignal(source="stale_expired")

    is_vip = False
    tier_label = None
    tier_rank_order = 0
    priority_score = None
    display_badge = None

    for mapping in config.field_mappings:
        val = walk_doc(raw_doc, mapping.external_field_path)

        if mapping.kind == FieldKind.BOOLEAN:
            # Coerce to bool
            bool_val = bool(val)
            if bool_val == mapping.boolean_true_means_vip:
                is_vip = True

        elif mapping.kind == FieldKind.ENUM:
            str_val = str(val) if val is not None else ""
            match = None
            for em in mapping.enum_mapping:
                if em.raw_value == str_val:
                    match = em
                    break

            if match is None:
                log.debug("external_directory.enum_miss", path=mapping.external_field_path, value=str_val)
                continue

            if match.is_vip:
                is_vip = True

            if match.rank_order > tier_rank_order:
                tier_rank_order = match.rank_order
                tier_label = match.rank_label

            if mapping.local_name == "display_badge" and match.rank_label:
                display_badge = match.rank_label

        elif mapping.kind == FieldKind.NUMERIC_THRESHOLD:
            try:
                num_val = float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                log.debug("external_directory.num_cast_failed", path=mapping.external_field_path, value=val)
                num_val = 0.0

            if mapping.numeric_vip_threshold is not None and num_val >= mapping.numeric_vip_threshold:
                is_vip = True

            score = num_val
            if mapping.numeric_max_for_scale is not None and mapping.numeric_max_for_scale > 0:
                score = (num_val / mapping.numeric_max_for_scale) * 100.0
                score = max(0.0, min(100.0, score))

            if mapping.local_name == "priority_score":
                priority_score = score

    return ResolvedUserSignal(
        is_vip=is_vip,
        tier_label=tier_label,
        tier_rank_order=tier_rank_order,
        priority_score=priority_score,
        display_badge=display_badge,
        source="external_directory",
    )
