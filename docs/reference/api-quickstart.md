# API Quickstart

Hands-on: from "fresh Railway deploy" to "first authenticated request"
in under five minutes.

## 0. Prerequisites

- XTV-SupportBot deployed with `API_ENABLED=true` (see
  [Railway deployment](../ops/railway.md))
- The bot is a member of your Telegram admin forum supergroup and you
  are in `ADMIN_IDS`
- `curl` + `jq` installed locally

Throughout this page we use the public Railway URL as `$BASE`:

```bash
export BASE=https://your-bot.up.railway.app
```

## 1. Verify the API is live

```bash
curl -sS $BASE/health | jq .
```

Expected:

```json
{"ok": true, "version": "0.9.0"}
```

If you get a hang or an HTML error page: the bot isn't serving HTTP
yet. Double-check `API_ENABLED=true` and `Procfile` is `web: python
main.py`.

## 2. Mint an API key

Open a DM with your bot and run:

```
/apikey create admin:full
```

The bot replies once with the plaintext key — copy it **immediately**,
you will not see it again (it's SHA-256 hashed at rest). Save it into
the env of whichever tool will call the API:

```bash
export XTV_KEY=xtv_abcdef1234567890abcdef1234567890abcdef12
```

!!! warning "Scopes matter"
    `admin:full` grants everything. For a production integration
    create a narrow key per consumer: `tickets:read`, `analytics:read`,
    `webhooks:write`, etc. See [authentication](api-auth.md) for the
    full scope list.

## 3. Your first request

```bash
curl -sS $BASE/api/v1/tickets?limit=5 \
     -H "Authorization: Bearer $XTV_KEY" | jq .
```

Response:

```json
{
  "count": 5,
  "items": [
    {
      "_id": "…",
      "status": "open",
      "priority": "high",
      "created_at": "…",
      …
    }
  ]
}
```

## 4. Browse OpenAPI in a browser

Visit `$BASE/api/v1/docs` — Swagger UI loads with every route, every
schema, and a "Try it out" button. Paste your key into the green
**Authorize** button (format `Bearer xtv_…`) and every subsequent
request inherits it.

For a cleaner reading view: `$BASE/api/v1/redoc`.

## 5. Write endpoints (Phase 4.7)

Close a ticket:

```bash
curl -sS -X POST $BASE/api/v1/tickets/<id>/close \
     -H "Authorization: Bearer $XTV_KEY" \
     -H "Content-Type: application/json" \
     -d '{"reason": "resolved"}' | jq .
```

Install a project from a built-in template:

```bash
curl -sS -X POST $BASE/api/v1/projects \
     -H "Authorization: Bearer $XTV_KEY" \
     -H "Content-Type: application/json" \
     -d '{"template_slug": "billing", "project_slug": "pay", "name": "Payments"}' | jq .
```

Subscribe a webhook:

```bash
curl -sS -X POST $BASE/api/v1/webhooks \
     -H "Authorization: Bearer $XTV_KEY" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/hook", "events": ["ticket.closed"]}' | jq .
```

The response includes a one-time `secret` — save it to verify future
deliveries (see [webhooks](webhooks.md)).

## 6. JavaScript fetch example

```javascript
const BASE = "https://your-bot.up.railway.app";
const KEY = localStorage.getItem("xtv_key");

async function recentTickets() {
  const res = await fetch(`${BASE}/api/v1/tickets?limit=10`, {
    headers: { Authorization: `Bearer ${KEY}` },
  });
  if (!res.ok) throw new Error(await res.text());
  const body = await res.json();
  return body.items;
}
```

The admin SPA in `web/` uses this exact pattern.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 missing_bearer` | Forgot the `Authorization` header | Add `-H "Authorization: Bearer $XTV_KEY"` |
| `401 invalid_key` | Wrong / revoked / typo key | Mint a new one with `/apikey create` |
| `403 insufficient_scope` | Key lacks a required scope | Revoke + recreate with the right scope, or grant `admin:full` if appropriate |
| `404` on `/api/v1/…` | API not started | Set `API_ENABLED=true`, restart |
| `503 database_unavailable` | MongoDB down or unreachable | Check `MONGO_URI` and the Mongo add-on |
| `429` | Rate-limit hit | Raise `API_RATE_LIMIT_PER_MINUTE` or throttle |

## Next

- [Authentication deep-dive](api-auth.md)
- [Write endpoints reference](api-write.md)
- [Outgoing webhooks](webhooks.md)
- [Railway deployment](../ops/railway.md)
