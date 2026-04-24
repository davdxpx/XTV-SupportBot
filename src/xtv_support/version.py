"""Single source of truth for the package version.

Kept deliberately tiny so tools (pyproject.toml dynamic-version, docs,
CLI ``--version``) can import it without pulling the whole package.
"""

from __future__ import annotations

__all__ = ["__version__", "VERSION"]

__version__: str = "0.9.0"
VERSION: str = __version__
