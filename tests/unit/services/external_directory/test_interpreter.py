import datetime

import pytest

from xtv_support.services.external_directory.interpreter import resolve_signal
from xtv_support.services.external_directory.model import (
    EnumRankMapping,
    ExternalDirectoryConfig,
    FieldKind,
    FieldMapping,
)


@pytest.fixture
def now():
    return datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC)


def test_resolve_signal_none_doc(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
    )
    sig = resolve_signal(None, config, now=now)
    assert not sig.is_vip
    assert sig.source == "none"


def test_resolve_signal_expired_iso(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        expiry_field_path="sub.ends_at",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_vip",
                kind=FieldKind.BOOLEAN,
            ),
        ),
    )
    doc = {"sub": {"ends_at": "2024-12-31T12:00:00Z"}, "is_vip": True}
    sig = resolve_signal(doc, config, now=now)

    assert not sig.is_vip
    assert sig.source == "stale_expired"


def test_resolve_signal_not_expired_iso(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        expiry_field_path="sub.ends_at",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_vip",
                kind=FieldKind.BOOLEAN,
            ),
        ),
    )
    doc = {"sub": {"ends_at": "2025-12-31T12:00:00Z"}, "is_vip": True}
    sig = resolve_signal(doc, config, now=now)

    assert sig.is_vip
    assert sig.source == "external_directory"


def test_resolve_signal_boolean_mapping_true(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_premium",
                kind=FieldKind.BOOLEAN,
                boolean_true_means_vip=True,
            ),
        ),
    )
    sig = resolve_signal({"is_premium": True}, config, now=now)
    assert sig.is_vip

    sig_false = resolve_signal({"is_premium": False}, config, now=now)
    assert not sig_false.is_vip


def test_resolve_signal_boolean_mapping_false(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_free",
                kind=FieldKind.BOOLEAN,
                boolean_true_means_vip=False,
            ),
        ),
    )
    sig = resolve_signal({"is_free": False}, config, now=now)
    assert sig.is_vip

    sig_false = resolve_signal({"is_free": True}, config, now=now)
    assert not sig_false.is_vip


def test_resolve_signal_enum_mapping(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        field_mappings=(
            FieldMapping(
                local_name="tier_label",
                external_field_path="tier",
                kind=FieldKind.ENUM,
                enum_mapping=(
                    EnumRankMapping("bronze", "Bronze", 1, False),
                    EnumRankMapping("silver", "Silver", 2, False),
                    EnumRankMapping("gold", "Gold", 3, True),
                ),
            ),
        ),
    )

    sig = resolve_signal({"tier": "silver"}, config, now=now)
    assert not sig.is_vip
    assert sig.tier_label == "Silver"
    assert sig.tier_rank_order == 2

    sig_gold = resolve_signal({"tier": "gold"}, config, now=now)
    assert sig_gold.is_vip
    assert sig_gold.tier_label == "Gold"
    assert sig_gold.tier_rank_order == 3

    sig_unknown = resolve_signal({"tier": "diamond"}, config, now=now)
    assert not sig_unknown.is_vip
    assert sig_unknown.tier_rank_order == 0


def test_resolve_signal_numeric_threshold(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        field_mappings=(
            FieldMapping(
                local_name="priority_score",
                external_field_path="loyalty",
                kind=FieldKind.NUMERIC_THRESHOLD,
                numeric_vip_threshold=100.0,
                numeric_max_for_scale=200.0,
            ),
        ),
    )

    sig_high = resolve_signal({"loyalty": 150}, config, now=now)
    assert sig_high.is_vip
    assert sig_high.priority_score == 75.0

    sig_low = resolve_signal({"loyalty": 50}, config, now=now)
    assert not sig_low.is_vip
    assert sig_low.priority_score == 25.0

    sig_err = resolve_signal({"loyalty": "bad"}, config, now=now)
    assert not sig_err.is_vip
    assert sig_err.priority_score == 0.0


def test_resolve_signal_multiple_mappings(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        field_mappings=(
            FieldMapping(
                local_name="vip_status",
                external_field_path="is_premium",
                kind=FieldKind.BOOLEAN,
            ),
            FieldMapping(
                local_name="display_badge",
                external_field_path="tier",
                kind=FieldKind.ENUM,
                enum_mapping=(EnumRankMapping("admin", "Admin Badge", 10, True),),
            ),
        ),
    )

    doc = {"is_premium": False, "tier": "admin"}
    sig = resolve_signal(doc, config, now=now)

    assert sig.is_vip  # from the second mapping OR'ing to true
    assert sig.display_badge == "Admin Badge"


def test_resolve_signal_datetime_expiry(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        expiry_field_path="expires",
    )

    doc = {"expires": now - datetime.timedelta(days=1)}
    sig = resolve_signal(doc, config, now=now)
    assert sig.source == "stale_expired"


def test_resolve_signal_epoch_expiry(now):
    config = ExternalDirectoryConfig(
        enabled=True,
        connection_uri_ref="ref",
        database_name="db",
        collection_name="coll",
        external_id_field="id",
        expiry_field_path="expires",
    )

    dt = now - datetime.timedelta(days=1)
    doc = {"expires": dt.timestamp()}
    sig = resolve_signal(doc, config, now=now)
    assert sig.source == "stale_expired"
