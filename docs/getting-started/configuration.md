# Configuration

All settings come from environment variables (or a `.env` file).
`.env.example` in the repo root is the canonical reference and is
kept in sync with the code.

## Core (required)

| Variable | Description |
|---|---|
| `API_ID` | Telegram API id (my.telegram.org). |
| `API_HASH` | Telegram API hash. |
| `BOT_TOKEN` | Bot token from @BotFather. |
| `MONGO_URI` | MongoDB connection URI. |
| `ADMIN_IDS` | Comma-separated Telegram user IDs that bootstrap as `role=admin`. |
| `ADMIN_CHANNEL_ID` | Forum supergroup id (usually `-100…`). |

## Feature flags

Every opt-in feature gets a `FEATURE_*` flag. See
[Reference → Environment](../reference/env.md) for the full list.

## Secrets rotation

Run `python scripts/rotate_secrets.py all` to mint fresh
`WEBHOOK_SECRET` / `CAPTCHA_SECRET` values. Paste into your deployment
env and redeploy.
