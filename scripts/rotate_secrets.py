#!/usr/bin/env python3
"""Rotate webhook + captcha shared secrets.

Outputs fresh random secrets to stdout. Operators copy them into their
env (Railway / systemd / compose) and redeploy. Grace-period handling
(old + new valid for 24h) is a service-side concern; this script only
mints the values.

Usage
-----
::

    python scripts/rotate_secrets.py webhook     # WEBHOOK_SECRET
    python scripts/rotate_secrets.py captcha     # CAPTCHA_SECRET
    python scripts/rotate_secrets.py all
"""

from __future__ import annotations

import secrets
import sys

KEYS: dict[str, str] = {
    "webhook": "WEBHOOK_SECRET",
    "captcha": "CAPTCHA_SECRET",
}


def mint() -> str:
    # 48 random bytes -> 64 URL-safe chars. HMAC-SHA-256 keys need at
    # least 32 bytes; we give 48 for headroom.
    return secrets.token_urlsafe(48)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 64
    kind = argv[1].lower()
    if kind == "all":
        for env_name in KEYS.values():
            print(f"{env_name}={mint()}")
        return 0
    if kind not in KEYS:
        print(f"Unknown kind: {kind}", file=sys.stderr)
        return 64
    print(f"{KEYS[kind]}={mint()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
