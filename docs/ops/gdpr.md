# GDPR & compliance

## User-facing commands

- `/gdpr export` — the bot sends a JSON document with the user's own
  `user`, `tickets`, `csat_responses`, and audit entries.
- `/gdpr delete` — marks `deleted_at` and schedules a hard purge after
  30 days (`DEFAULT_GRACE_DAYS`). The user is blocked immediately.

## Admin override

- Soft-delete requests can be cancelled inside the grace window via
  `/admin users` → "Cancel pending deletion".
- `/gdpr purge-audit <days>` trims `audit_log` ad-hoc when you need
  to reclaim retention.

## Audit trail

Every privileged action goes to `audit_log` with a TTL set from
`AUDIT_RETENTION_DAYS`. The default retention is 90 days.

## Secrets

Rotate with `python scripts/rotate_secrets.py all` whenever:

- A team member rotates credentials.
- You suspect a leak.
- A webhook consumer's key is compromised.
