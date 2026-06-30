"""Password hashing for admin accounts.

Argon2id via ``argon2-cffi`` with the library's recommended defaults.
A single :class:`PasswordHasher` is reused process-wide — it is
stateless and thread-safe. Plaintext passwords and hashes are never
logged anywhere in this module or its callers.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plaintext: str) -> str:
    """Return an Argon2id hash for ``plaintext``."""
    return _hasher.hash(plaintext)


def verify_password(password_hash: str, plaintext: str) -> bool:
    """Constant-time verify (handled by argon2). Never raises."""
    try:
        return _hasher.verify(password_hash, plaintext)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
