# GDPR & compliance

## User-facing commands

Both live in the user's DM with the bot and are wired to the
real services in `xtv_support.services.gdpr`.

- **`/gdpr_export`** — the bot runs
  [`exporter.build_export`](https://github.com/davdxpx/XTV-SupportBot/blob/main/src/xtv_support/services/gdpr/exporter.py)
  for the calling user and sends back a single `xtv_export_<user_id>.json`
  document with every section the bot stores about them: their `user`
  record, their `tickets`, their CSAT responses, and their audit
  entries. Safe to run repeatedly.
- **`/gdpr_delete`** — two-step:
    1. The bot replies with a warning card that lists the grace window
       (default 30 days, from `DEFAULT_GRACE_DAYS`) and offers
       **✅ Yes, delete my data** / **◀ Cancel** buttons.
    2. Confirm → the bot calls
       [`deleter.request_deletion`](https://github.com/davdxpx/XTV-SupportBot/blob/main/src/xtv_support/services/gdpr/deleter.py),
       which sets `users.deleted_at` and blocks the user from the bot
       immediately. A periodic task (`purge_expired`) hard-deletes
       the record after the grace window.

The same two actions are reachable from `/settings` → 📥 Export my
data / 🗑 Delete my data.

## Admin override

Admins can cancel a pending deletion inside the grace window by
calling `deleter.cancel_deletion(db, user_id)` — there is no
dedicated Telegram command yet; run it from the container shell or a
small admin script.

## Audit trail

Every privileged action goes to `audit_log` with a TTL set from
`AUDIT_RETENTION_DAYS`. The default retention is 90 days.

## Secrets

Rotate with `python scripts/rotate_secrets.py all` whenever:

- A team member rotates credentials.
- You suspect a leak.
- A webhook consumer's key is compromised.
