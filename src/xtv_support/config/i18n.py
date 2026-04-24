"""Locale-file loader.

The runtime :class:`~xtv_support.core.i18n.I18n` is pure in-memory — it
doesn't touch the filesystem. This module knows where on disk the YAML
files live and how to parse them.

Two loaders:

* :func:`load_locales` — production entry-point: reads every ``*.yaml``
  under :data:`LOCALES_DIR` and returns ``{code: mapping}``.
* :func:`load_locales_from` — explicit directory for tests and
  hot-reload scenarios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ``src/xtv_support/locales``
LOCALES_DIR: Path = Path(__file__).resolve().parent.parent / "locales"


class LocaleLoadError(RuntimeError):
    """Raised when a locale file is malformed."""


def load_locales_from(directory: Path) -> dict[str, dict[str, Any]]:
    """Parse every ``*.yaml`` under ``directory`` into ``{code: data}``."""
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise LocaleLoadError(f"Locales path is not a directory: {directory}")

    out: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        code = path.stem
        try:
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise LocaleLoadError(f"{path.name}: {exc}") from exc
        if not isinstance(data, dict):
            raise LocaleLoadError(
                f"{path.name}: expected a mapping at root, got {type(data).__name__}"
            )
        out[code] = data
    return out


def load_locales() -> dict[str, dict[str, Any]]:
    """Load every bundled locale from :data:`LOCALES_DIR`."""
    return load_locales_from(LOCALES_DIR)


def list_supported(locales: dict[str, dict[str, Any]]) -> list[tuple[str, str, str]]:
    """Return ``[(code, native_name, flag), ...]`` for UI pickers."""
    out: list[tuple[str, str, str]] = []
    for code, data in sorted(locales.items()):
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        native = str(meta.get("native_name", code)) if isinstance(meta, dict) else code
        flag = str(meta.get("flag", "")) if isinstance(meta, dict) else ""
        out.append((code, native, flag))
    return out
