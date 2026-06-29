from __future__ import annotations

import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from xtv_support.services.external_directory.model import (
    EnumRankMapping,
    ExternalDirectoryConfig,
    FieldKind,
    FieldMapping,
)


def _doc_to_config(doc: dict[str, Any]) -> ExternalDirectoryConfig:
    field_mappings_raw = doc.get("field_mappings", [])
    field_mappings = []

    for fdoc in field_mappings_raw:
        enum_mapping_raw = fdoc.get("enum_mapping", [])
        enum_mapping = tuple(
            EnumRankMapping(
                raw_value=edoc.get("raw_value", ""),
                is_vip=edoc.get("is_vip", False),
                rank_order=edoc.get("rank_order", 0),
                rank_label=edoc.get("rank_label", ""),
            )
            for edoc in enum_mapping_raw
        )

        kind_str = fdoc.get("kind", "BOOLEAN")
        kind = (
            FieldKind(kind_str) if kind_str in [e.value for e in FieldKind] else FieldKind.BOOLEAN
        )

        fm = FieldMapping(
            external_field_path=fdoc.get("external_field_path", ""),
            local_name=fdoc.get("local_name", ""),
            kind=kind,
            boolean_true_means_vip=fdoc.get("boolean_true_means_vip", False),
            numeric_vip_threshold=fdoc.get("numeric_vip_threshold"),
            numeric_max_for_scale=fdoc.get("numeric_max_for_scale"),
            enum_mapping=enum_mapping,
        )
        field_mappings.append(fm)

    last_verified_at = doc.get("last_verified_at")
    if isinstance(last_verified_at, str):
        try:
            last_verified_at = datetime.datetime.fromisoformat(last_verified_at)
        except ValueError:
            last_verified_at = None

    return ExternalDirectoryConfig(
        enabled=doc.get("enabled", False),
        database_name=doc.get("database_name", ""),
        collection_name=doc.get("collection_name", ""),
        external_id_field=doc.get("external_id_field", "_id"),
        external_id_is_string=doc.get("external_id_is_string", True),
        expiry_field_path=doc.get("expiry_field_path"),
        field_mappings=tuple(field_mappings),
        connection_uri_ref=doc.get("connection_uri_ref", "env"),
        last_verified_at=last_verified_at,
        last_verification_error=doc.get("last_verification_error"),
    )


def _config_to_doc(config: ExternalDirectoryConfig) -> dict[str, Any]:
    field_mappings_docs = []
    for fm in config.field_mappings:
        enum_mapping_docs = [
            {
                "raw_value": em.raw_value,
                "is_vip": em.is_vip,
                "rank_order": em.rank_order,
                "rank_label": em.rank_label,
            }
            for em in fm.enum_mapping
        ]

        fdoc = {
            "external_field_path": fm.external_field_path,
            "local_name": fm.local_name,
            "kind": fm.kind.value,
            "boolean_true_means_vip": fm.boolean_true_means_vip,
            "numeric_vip_threshold": fm.numeric_vip_threshold,
            "numeric_max_for_scale": fm.numeric_max_for_scale,
            "enum_mapping": enum_mapping_docs,
        }
        field_mappings_docs.append(fdoc)

    return {
        "_id": "singleton",
        "enabled": config.enabled,
        "database_name": config.database_name,
        "collection_name": config.collection_name,
        "external_id_field": config.external_id_field,
        "external_id_is_string": config.external_id_is_string,
        "expiry_field_path": config.expiry_field_path,
        "field_mappings": field_mappings_docs,
        "connection_uri_ref": config.connection_uri_ref,
        "last_verified_at": config.last_verified_at.isoformat()
        if config.last_verified_at
        else None,
        "last_verification_error": config.last_verification_error,
    }


async def get_config(db: AsyncIOMotorDatabase) -> ExternalDirectoryConfig | None:
    """Retrieve the active external directory configuration."""
    doc = await db.external_directory_config.find_one({"_id": "singleton"})
    if not doc:
        return None
    return _doc_to_config(doc)


async def save_config(db: AsyncIOMotorDatabase, config: ExternalDirectoryConfig) -> None:
    """Save the external directory configuration.

    The connection string is opaque here and handled securely through secret storage.
    """
    doc = _config_to_doc(config)
    await db.external_directory_config.update_one(
        {"_id": "singleton"},
        {"$set": doc},
        upsert=True,
    )


async def clear_config(db: AsyncIOMotorDatabase) -> None:
    """Disable and clear the external directory configuration and secrets."""
    await db.external_directory_config.delete_one({"_id": "singleton"})
    await db.external_directory_secrets.delete_one({"_id": "singleton"})

    # TODO(prompt-3): invalidate live provider cache here
