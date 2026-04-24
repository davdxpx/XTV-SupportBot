"""PluginRegistry tests."""

from __future__ import annotations

import pytest

from xtv_support.plugins.base import LoadedPlugin, Plugin
from xtv_support.plugins.registry import PluginRegistry


class _P(Plugin):
    name = "dummy"
    version = "0.0.1"


def test_add_and_get() -> None:
    r = PluginRegistry()
    entry = LoadedPlugin(plugin=_P(), source="builtin", status="loaded")
    r.add(entry)
    assert len(r) == 1
    assert r.get("dummy") is entry
    assert "dummy" in r


def test_add_requires_name() -> None:
    p = _P()
    p.name = ""
    r = PluginRegistry()
    with pytest.raises(ValueError):
        r.add(LoadedPlugin(plugin=p, source="builtin"))


def test_duplicate_add_raises() -> None:
    r = PluginRegistry()
    r.add(LoadedPlugin(plugin=_P(), source="builtin"))
    with pytest.raises(ValueError):
        r.add(LoadedPlugin(plugin=_P(), source="builtin"))


def test_status_filters() -> None:
    r = PluginRegistry()

    class A(Plugin):
        name = "a"

    class B(Plugin):
        name = "b"

    class C(Plugin):
        name = "c"

    r.add(LoadedPlugin(plugin=A(), source="builtin", status="loaded"))
    r.add(LoadedPlugin(plugin=B(), source="builtin", status="failed", error="x"))
    r.add(LoadedPlugin(plugin=C(), source="builtin", status="disabled"))

    assert [e.plugin.name for e in r.loaded()] == ["a"]
    assert [e.plugin.name for e in r.failed()] == ["b"]
    assert [e.plugin.name for e in r.disabled()] == ["c"]


def test_require_raises_for_missing() -> None:
    r = PluginRegistry()
    with pytest.raises(KeyError):
        r.require("nope")


def test_remove_returns_entry() -> None:
    r = PluginRegistry()
    r.add(LoadedPlugin(plugin=_P(), source="builtin"))
    removed = r.remove("dummy")
    assert removed is not None
    assert "dummy" not in r
    assert r.remove("dummy") is None


def test_clear() -> None:
    r = PluginRegistry()
    r.add(LoadedPlugin(plugin=_P(), source="builtin"))
    r.clear()
    assert len(r) == 0
