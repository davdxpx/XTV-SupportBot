"""GDPR exporter tests."""
from __future__ import annotations

from datetime import datetime, timezone

from xtv_support.services.gdpr.exporter import ExportBundle, _jsonable, _jsonable_value


def test_jsonable_value_datetime_serialised() -> None:
    v = _jsonable_value(datetime(2026, 4, 20, 10, tzinfo=timezone.utc))
    assert v == "2026-04-20T10:00:00+00:00"


def test_jsonable_value_primitives_passthrough() -> None:
    assert _jsonable_value(42) == 42
    assert _jsonable_value(3.14) == 3.14
    assert _jsonable_value("x") == "x"
    assert _jsonable_value(True) is True
    assert _jsonable_value(None) is None


def test_jsonable_value_list_recurses() -> None:
    out = _jsonable_value([1, "x", datetime(2026, 1, 1, tzinfo=timezone.utc)])
    assert out == [1, "x", "2026-01-01T00:00:00+00:00"]


def test_jsonable_doc_converts_keys_to_strings() -> None:
    out = _jsonable({"user_id": 7, "nested": {"a": 1}})
    assert out == {"user_id": 7, "nested": {"a": 1}}


def test_jsonable_non_dict_returns_empty_dict() -> None:
    assert _jsonable("scalar") == {}


def test_bundle_to_json_shape() -> None:
    b = ExportBundle(
        user_id=7,
        generated_at=datetime(2026, 4, 20, 10, tzinfo=timezone.utc),
        sections={"user": [{"user_id": 7}], "tickets": []},
    )
    js = b.to_json()
    assert js["user_id"] == 7
    assert js["generated_at"] == "2026-04-20T10:00:00+00:00"
    assert js["sections"]["user"][0]["user_id"] == 7
    assert js["sections"]["tickets"] == []
