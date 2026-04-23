"""Pure domain layer — dataclasses, enums and events with no IO.

Everything under `domain/` must be importable with zero side effects.
Adapters that touch databases, Telegram, Redis, HTTP, … live under
`xtv_support.infrastructure` instead.
"""
