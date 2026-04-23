"""Process-wide registry of loaded plugins.

The registry is just an ordered dict wrapped in a small API so the
dashboard and the ``/admin » Plugins`` view can enumerate plugins along
with their status without reaching into the loader's internals.
"""
from __future__ import annotations

from collections.abc import Iterable

from xtv_support.plugins.base import LoadedPlugin


class PluginRegistry:
    """Name-indexed store of :class:`LoadedPlugin` entries."""

    __slots__ = ("_by_name",)

    def __init__(self) -> None:
        self._by_name: dict[str, LoadedPlugin] = {}

    def add(self, entry: LoadedPlugin) -> None:
        if not entry.plugin.name:
            raise ValueError("Plugin.name must be set before registration.")
        if entry.plugin.name in self._by_name:
            raise ValueError(f"Plugin {entry.plugin.name!r} is already registered.")
        self._by_name[entry.plugin.name] = entry

    def get(self, name: str) -> LoadedPlugin | None:
        return self._by_name.get(name)

    def require(self, name: str) -> LoadedPlugin:
        entry = self._by_name.get(name)
        if entry is None:
            raise KeyError(f"No plugin named {name!r} is registered.")
        return entry

    def remove(self, name: str) -> LoadedPlugin | None:
        return self._by_name.pop(name, None)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._by_name

    def __iter__(self) -> Iterable[LoadedPlugin]:  # type: ignore[override]
        return iter(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)

    def all(self) -> list[LoadedPlugin]:
        return list(self._by_name.values())

    def loaded(self) -> list[LoadedPlugin]:
        return [e for e in self._by_name.values() if e.status == "loaded"]

    def failed(self) -> list[LoadedPlugin]:
        return [e for e in self._by_name.values() if e.status == "failed"]

    def disabled(self) -> list[LoadedPlugin]:
        return [e for e in self._by_name.values() if e.status == "disabled"]

    def clear(self) -> None:
        """Drop every entry — intended for tests."""
        self._by_name.clear()
