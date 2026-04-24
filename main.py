"""Thin wrapper — run with ``python main.py``.

Kept at repo root so Railway / Nixpacks / Heroku buildpacks and existing
``Procfile`` consumers keep working without config changes. The real boot
logic lives in :mod:`xtv_support.__main__`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make ``src/`` importable when running the file directly without installing
# the package (``python main.py`` from a fresh clone).
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from xtv_support import entrypoint  # noqa: E402 — after sys.path tweak

if __name__ == "__main__":
    entrypoint()
