import datetime

from xtv_support.infrastructure.db.external_directory_config import _config_to_doc, _doc_to_config
from xtv_support.services.external_directory.model import (
    EnumRankMapping,
    ExternalDirectoryConfig,
    FieldKind,
    FieldMapping,
)


def test_config_doc_round_trip():
    original_config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="env",
        database_name="mydb",
        collection_name="users",
        external_id_field="uid",
        external_id_is_string=True,
        expiry_field_path="meta.expires_at",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_vip",
                kind=FieldKind.BOOLEAN,
                boolean_true_means_vip=True,
            ),
            FieldMapping(
                local_name="tier_label",
                external_field_path="subscription.tier",
                kind=FieldKind.ENUM,
                enum_mapping=(
                    EnumRankMapping(
                        raw_value="gold", rank_label="Gold", rank_order=10, is_vip=True
                    ),
                    EnumRankMapping(
                        raw_value="free", rank_label="Free", rank_order=0, is_vip=False
                    ),
                ),
            ),
            FieldMapping(
                local_name="priority_score",
                external_field_path="stats.score",
                kind=FieldKind.NUMERIC_THRESHOLD,
                numeric_vip_threshold=100.0,
                numeric_max_for_scale=1000.0,
            ),
        ),
        last_verified_at=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC),
        last_verification_error=None,
    )

    doc = _config_to_doc(original_config)
    assert doc["_id"] == "singleton"

    rehydrated_config = _doc_to_config(doc)
    assert original_config == rehydrated_config
