"""Runtime translator.

Lookup is two-level:

1. Try the requested ``locale``; dotted keys navigate nested maps
   (``user.welcome`` -> ``locales["en"]["user"]["welcome"]``).
2. Fall back to the configured default locale.
3. If still missing, return the key itself — UI shows it instead of
   silently rendering nothing, so missing strings get noticed fast.

Plurals
-------
If ``count`` is a keyword argument and an integer, the translator also
tries ``{key}_one`` (when ``count == 1``) and ``{key}_other`` (otherwise)
before falling back to ``{key}``. This is the simplest form of ICU
plurals and handles English/Spanish/Russian-simple cases without extra
dependencies.

Formatting
----------
Templates use ``str.format`` style placeholders::

    "Welcome, {name}!"
    "You have {count} open tickets."

A missing placeholder is non-fatal — the raw template is returned so the
bot never crashes just because a caller forgot to pass ``name``. A
warning is logged on the ``xtv_support.i18n`` logger.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xtv_support.core.logger import get_logger

_log = get_logger("xtv_support.i18n")


class I18n:
    """Tiny, dependency-free translator."""

    __slots__ = ("_locales", "_default")

    def __init__(
        self,
        locales: Mapping[str, Mapping[str, Any]],
        default_lang: str = "en",
    ) -> None:
        self._locales: dict[str, Mapping[str, Any]] = dict(locales)
        self._default = default_lang

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def t(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """Translate ``key`` into ``locale`` (or the default when ``None``)."""
        template = self._resolve(key, locale, kwargs)
        if template is None:
            _log.warning("i18n.missing_key", key=key, locale=locale or self._default)
            return key
        return self._format(template, kwargs)

    def has(self, key: str, locale: str | None = None) -> bool:
        return self._lookup(key, locale) is not None

    @property
    def default_lang(self) -> str:
        return self._default

    def supported(self) -> list[str]:
        return sorted(self._locales.keys())

    def locale(self, code: str) -> Mapping[str, Any] | None:
        return self._locales.get(code)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve(
        self, key: str, locale: str | None, kwargs: Mapping[str, Any]
    ) -> str | None:
        """Pick the right template considering plural suffixes."""
        count = kwargs.get("count")
        if isinstance(count, int):
            suffix = "_one" if count == 1 else "_other"
            template = self._lookup(f"{key}{suffix}", locale)
            if template is not None:
                return template
        return self._lookup(key, locale)

    def _lookup(self, key: str, locale: str | None) -> str | None:
        """Try ``locale`` first, then ``default_lang``. Returns ``None`` if neither hits."""
        seen: set[str] = set()
        for lang in (locale, self._default):
            if not lang or lang in seen:
                continue
            seen.add(lang)
            data = self._locales.get(lang)
            if data is None:
                continue
            value = _walk_dotted(data, key)
            if isinstance(value, str):
                return value
        return None

    @staticmethod
    def _format(template: str, kwargs: Mapping[str, Any]) -> str:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError) as exc:
            _log.warning(
                "i18n.placeholder_missing",
                template=template,
                error=str(exc),
                provided=list(kwargs.keys()),
            )
            return template


def _walk_dotted(data: Mapping[str, Any], dotted: str) -> Any:
    """Return the value at ``dotted`` (e.g. ``user.welcome``) or ``None``."""
    cursor: Any = data
    for part in dotted.split("."):
        if not isinstance(cursor, Mapping):
            return None
        cursor = cursor.get(part)
        if cursor is None:
            return None
    return cursor
