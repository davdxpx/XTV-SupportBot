# API authentication

XTV-SupportBot uses long-lived **API keys** with **scopes**. Keys are
minted from the Telegram bot (there is no HTTP signup / password flow),
stored SHA-256-hashed at rest, and carried as `Authorization: Bearer`.

## Key format

```
xtv_<40 url-safe chars>
```

- Prefix `xtv_` — quick visual identification.
- 40 url-safe base64 characters — 240 bits of entropy.
- Total: 44 characters. Small enough for headers, large enough that
  brute-force is not the attack you should worry about.

## Creating a key

Open a DM with the bot as an admin and run:

```
/apikey create <scope> [label]
```

Example:

```
/apikey create tickets:read reporting-service
```

The bot replies **once** with the plaintext key. After that it exists
only as a SHA-256 hash in the `api_keys` collection — there is no way
to re-read it. Store it immediately in a secrets manager (or at least
an `.env` file you can rotate).

Other admin commands:

| Command | Purpose |
|---|---|
| `/apikey list` | Show every key (label, scopes, last-used, revoked status) |
| `/apikey revoke <key_id>` | Immediately invalidate a key |

## Scopes

A key carries a list of scope strings. Routes declare which scope they
need; the dependency resolver raises 401 / 403 with a structured
`detail` block so the caller knows exactly what was missing.

| Scope | Grants |
|---|---|
| `tickets:read` | `GET /api/v1/tickets…` |
| `tickets:write` | `POST /api/v1/tickets/{id}/…` (close, assign, tags, priority, notes, bulk-action) |
| `projects:read` | `GET /api/v1/projects…` |
| `projects:write` | `POST /api/v1/projects`, `DELETE /api/v1/projects/{slug}` |
| `users:read` | `GET /api/v1/users…` (reserved — lands in a later release) |
| `analytics:read` | `GET /api/v1/analytics/summary` |
| `rules:read` | `GET /api/v1/rules` / `/api/v1/rules/{id}` |
| `webhooks:write` | `GET / POST / DELETE /api/v1/webhooks` |
| `admin:full` | Every scope above — reserve for human admins or trusted services |

### Assigning multiple scopes

Pass multiple scope strings separated by commas:

```
/apikey create tickets:read,analytics:read reporting
```

### Philosophy

- **Narrow keys per consumer.** Your CRM sync doesn't need
  `admin:full`; `tickets:read,tickets:write` is enough.
- **Rotate on departure.** When an integration is decommissioned,
  revoke its key rather than "soft-delete" the integration.
- **One key per tool.** If two services share a key, you can't revoke
  one without breaking the other.

## Using a key

```http
Authorization: Bearer xtv_<40-char-secret>
```

Example:

```bash
curl -sS $BASE/api/v1/tickets \
     -H "Authorization: Bearer xtv_abcdef..."
```

## Error semantics

| Status | Body | Meaning |
|---|---|---|
| `401` | `{"detail": "missing_bearer"}` | No `Authorization` header |
| `401` | `{"detail": "invalid_key"}` | Prefix wrong, key revoked, or hash mismatch |
| `403` | `{"detail": {"error": "insufficient_scope", "required": "X", "granted": [...]}}` | Key valid but lacks the required scope |

## Rotation playbook

When a secret leaks or a team member rotates out:

1. **Mint the replacement first.** `/apikey create <scope> label-v2`.
2. **Swap in-production config.** Update the secret store / env var on
   every consumer; roll the deploy.
3. **Verify new key works.** `curl $BASE/api/v1/version` with the new
   key.
4. **Revoke the old key.** `/apikey revoke <old_id>` — this is a hard
   cut-off; there is no grace period by design.
5. **Audit the access log.** Check the Mongo `audit_log` collection
   for any unexpected access using the old key's ID.

## Leak response checklist

If a key is posted publicly (GitHub push, pastebin, Discord…):

- [ ] Revoke the key immediately with `/apikey revoke <id>`
- [ ] Rotate related credentials (Mongo, Telegram bot token if
      exposed together)
- [ ] Pull last 24h of `audit_log` filtered by that key's label
- [ ] If write scopes were granted: check `ActionExecuted` events for
      unexpected close / assign / reply operations
- [ ] If `webhooks:write` was granted: list all
      `webhook_subscriptions` and revoke any the caller didn't create
- [ ] Post a short incident note in the admin topic (what was leaked,
      what was revoked, what was audited — a minute of writing now
      saves an afternoon of forensics later)

## Storage model

Stored document shape:

```json
{
  "_id": ObjectId,
  "hash": "sha256-hex",
  "label": "reporting-service",
  "scopes": ["tickets:read", "analytics:read"],
  "created_by": 123,
  "created_at": "2026-04-24T11:00:00Z",
  "last_used_at": "2026-04-24T12:15:03Z",
  "revoked_at": null
}
```

`last_used_at` is bumped best-effort on every successful lookup — it's
the fastest way to spot dead integrations on the next review.
