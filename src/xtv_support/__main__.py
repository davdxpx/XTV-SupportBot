"""Executable entry — ``python -m xtv_support``.

Populated by Phase 2c when ``app.bootstrap`` is moved across. Until then
this module only acts as an import target for :func:`xtv_support.entrypoint`.
"""
from __future__ import annotations


def entrypoint() -> None:
    """Launch the bot. Real implementation lands in Phase 2c."""
    raise NotImplementedError(
        "xtv_support.__main__.entrypoint is wired up in Phase 2c. "
        "For now, run `python main.py` from the repo root.",
    )


if __name__ == "__main__":
    entrypoint()
