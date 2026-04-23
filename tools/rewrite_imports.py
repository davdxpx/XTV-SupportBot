#!/usr/bin/env python3
"""One-shot import rewriter for Phase 2c.

Walks every *.py under ``src/``, ``tests/`` and the repo root and rewrites
``app.*`` import paths to the new ``xtv_support.*`` layout. Intentionally
conservative: only touches line-prefixes that start with ``from app`` or
``import app``.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Order matters — longer keys first so we don't clobber shorter matches.
SIMPLE_PREFIX_REPLACEMENTS: list[tuple[str, str]] = [
    # Services: legacy `app.services.X_service` -> `xtv_support.services.X.service`
    ("from app.services.ticket_service import",    "from xtv_support.services.tickets.service import"),
    ("from app.services.topic_service import",     "from xtv_support.services.tickets.topic_service import"),
    ("from app.services.broadcast_service import", "from xtv_support.services.broadcasts.service import"),
    ("from app.services.cooldown_service import",  "from xtv_support.services.cooldown.service import"),
    ("from app.services.sla_service import",       "from xtv_support.services.sla.service import"),
    ("from app.services.autoclose_service import", "from xtv_support.services.autoclose.service import"),
    # `from app.services import ticket_service` -> aliased import from tickets pkg
    ("from app.services import ticket_service, topic_service",
        "from xtv_support.services.tickets import service as ticket_service, topic_service"),
    ("from app.services import ticket_service",
        "from xtv_support.services.tickets import service as ticket_service"),
    ("from app.services import topic_service",
        "from xtv_support.services.tickets import topic_service"),
    ("from app.services import autoclose_service",
        "from xtv_support.services.autoclose import service as autoclose_service"),
    ("from app.services import broadcast_service",
        "from xtv_support.services.broadcasts import service as broadcast_service"),
    ("from app.services import cooldown_service",
        "from xtv_support.services.cooldown import service as cooldown_service"),
    ("from app.services import sla_service",
        "from xtv_support.services.sla import service as sla_service"),

    # UI primitives moved to ui/primitives/, keyboards to ui/keyboards/base
    ("from app.ui.blockquote import", "from xtv_support.ui.primitives.blockquote import"),
    ("from app.ui.card import",       "from xtv_support.ui.primitives.card import"),
    ("from app.ui.glyphs import",     "from xtv_support.ui.primitives.glyphs import"),
    ("from app.ui.progress import",   "from xtv_support.ui.primitives.progress import"),
    ("from app.ui.keyboards import",  "from xtv_support.ui.keyboards.base import"),

    # Config + bootstrap + constants landed at specific new paths
    ("from app.config import",    "from xtv_support.config.settings import"),
    ("from app.bootstrap import", "from xtv_support.core.bootstrap import"),
    ("from app.constants import", "from xtv_support.core.constants import"),

    # DB → infrastructure/db
    ("from app.db.",              "from xtv_support.infrastructure.db."),
    ("from app.db import",        "from xtv_support.infrastructure.db import"),

    # Straight package-prefix rewrites for what already has the right sublayout
    ("from app.core.",        "from xtv_support.core."),
    ("from app.middlewares.", "from xtv_support.middlewares."),
    ("from app.handlers.",    "from xtv_support.handlers."),
    ("from app.tasks.",       "from xtv_support.tasks."),
    ("from app.tasks import", "from xtv_support.tasks import"),
    ("from app.ui.templates.", "from xtv_support.ui.templates."),
    ("from app.ui.templates import", "from xtv_support.ui.templates import"),
    ("from app.utils.",       "from xtv_support.utils."),
]

# Regex catch-all for bare ``import app...`` lines (rare here, but safe).
IMPORT_APP_RE = re.compile(r"^(\s*)import\s+app(\.[\w.]+)?\b")


def rewrite_content(text: str) -> tuple[str, int]:
    """Return (new_text, replacement_count)."""
    count = 0
    for old, new in SIMPLE_PREFIX_REPLACEMENTS:
        if old in text:
            occurrences = text.count(old)
            text = text.replace(old, new)
            count += occurrences

    # bare ``import app[.x.y]`` fallback (very rare)
    def _sub(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        prefix, tail = match.group(1), match.group(2) or ""
        return f"{prefix}import xtv_support{tail}"

    text, n = IMPORT_APP_RE.subn(_sub, text)
    count += n
    return text, count


def iter_py_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for base in ("src", "tests"):
        base_path = ROOT / base
        if base_path.exists():
            out.extend(base_path.rglob("*.py"))
    # also the top-level main.py if present
    top_main = ROOT / "main.py"
    if top_main.exists():
        out.append(top_main)
    return out


def main() -> int:
    dry_run = "--dry" in sys.argv
    total_files = 0
    total_changes = 0
    for path in iter_py_files():
        text = path.read_text(encoding="utf-8")
        new_text, count = rewrite_content(text)
        if count:
            total_files += 1
            total_changes += count
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
            print(f"{path.relative_to(ROOT)}: {count} rewrites")
    print("-" * 40)
    print(f"Files touched: {total_files}")
    print(f"Lines rewritten: {total_changes}")
    print("(dry-run)" if dry_run else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
