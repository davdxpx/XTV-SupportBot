"""Locale loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from xtv_support.config.i18n import (
    LOCALES_DIR,
    LocaleLoadError,
    list_supported,
    load_locales,
    load_locales_from,
)


def test_load_locales_from_nonexistent_dir_returns_empty(tmp_path: Path) -> None:
    assert load_locales_from(tmp_path / "missing") == {}


def test_load_locales_from_file_path_raises(tmp_path: Path) -> None:
    f = tmp_path / "foo.txt"
    f.write_text("not a dir")
    with pytest.raises(LocaleLoadError):
        load_locales_from(f)


def test_load_locales_from_picks_up_yaml(tmp_path: Path) -> None:
    (tmp_path / "en.yaml").write_text("meta:\n  code: en\nuser:\n  hi: Hello\n")
    (tmp_path / "es.yaml").write_text("meta:\n  code: es\nuser:\n  hi: Hola\n")
    out = load_locales_from(tmp_path)
    assert set(out) == {"en", "es"}
    assert out["en"]["user"]["hi"] == "Hello"
    assert out["es"]["user"]["hi"] == "Hola"


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text(":: not: valid\n  - one\n- two: three")
    with pytest.raises(LocaleLoadError):
        load_locales_from(tmp_path)


def test_root_not_mapping_raises(tmp_path: Path) -> None:
    (tmp_path / "scalar.yaml").write_text("just a string\n")
    with pytest.raises(LocaleLoadError):
        load_locales_from(tmp_path)


def test_bundled_locales_load() -> None:
    out = load_locales()
    # At minimum these 11 codes must be present.
    assert {"en", "ru", "es", "hi", "bn", "ta", "te", "mr", "pa", "gu", "ur"} <= set(out)
    # Every locale file must declare its meta.code.
    for code, data in out.items():
        assert data.get("meta", {}).get("code") == code, code
    # English has the full set — verify a couple of deeper keys exist.
    assert out["en"]["user"]["welcome"].startswith("👋")
    assert out["en"]["ticket"]["count_one"] == "1 ticket"


def test_bundled_locales_dir_exists() -> None:
    assert LOCALES_DIR.is_dir()


def test_list_supported_returns_tuples() -> None:
    out = load_locales()
    items = list_supported(out)
    codes = [c for c, _, _ in items]
    assert "en" in codes
    assert "hi" in codes
    # native_name field is picked up
    native_by_code = {c: n for c, n, _ in items}
    assert native_by_code["en"] == "English"
    assert native_by_code["hi"] == "हिन्दी"
