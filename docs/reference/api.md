# REST API reference

The REST API turns your XTV-SupportBot into a programmable helpdesk. Build
dashboards, pull analytics into BI tools, sync tickets to external CRMs,
or drive the admin SPA that ships in `web/`.

!!! info "Status in v0.9.0"
    Read-only endpoints (`GET /api/v1/tickets[/{id}]`, `GET /api/v1/projects`,
    `GET /api/v1/analytics/summary`) are production-ready. Write endpoints
    (reply, close, register webhook) are scaffolded and land in a later
    release. The health/readiness/metrics endpoints are always available.

## Base URL

The API binds to `0.0.0.0:$PORT` when `API_ENABLED=true`. On Railway the
public URL is the service's auto-generated domain, e.g.
`https://your-bot.up.railway.app`. Self-hosted it's whatever reverse proxy
fronts the container.

All examples below use `$BASE` as shorthand:

```bash
export BASE=https://your-bot.up.railway.app
```

## Enabling the API

1. Set `API_ENABLED=true` in your environment.
2. Deploy. On Railway, Render, Fly, or Heroku, `$PORT` is injected by the
   platform and takes precedence over `API_PORT`. Locally you can set
   `API_PORT=8000` (or anything free).
3. Check `$BASE/health` — expected response: `{"ok": true, "version": "0.9.0"}`.
4. Create an API key with `/apikey create admin:full` in the bot admin DM.

See [Quickstart](api-quickstart.md) for a full end-to-end walkthrough with
curl and JavaScript.

## Authentication

Every endpoint except `/health`, `/ready`, `/metrics`, `/api/v1/version`
and the OpenAPI endpoints requires the header:

```http
Authorization: Bearer xtv_<40-char-secret>
```

Keys are created from the Telegram bot — there is no password-based login
and no key creation over HTTP. See [API authentication](api-auth.md) for
the full lifecycle.

## OpenAPI & interactive docs

FastAPI auto-generates both a Swagger UI and a ReDoc view:

| Endpoint | Purpose |
|---|---|
| `GET $BASE/api/v1/docs` | Swagger UI — try requests in the browser |
| `GET $BASE/api/v1/redoc` | ReDoc — nicer for reading |
| `GET $BASE/api/v1/openapi.json` | Raw OpenAPI 3.1 schema |

!!! tip
    Lock the docs endpoints behind CORS in production by setting
    `API_CORS_ORIGINS=https://admin.your-domain.com` — the docs still
    render locally, but cross-origin reads are blocked.

## Endpoint catalogue

| Method | Path | Scope | Purpose |
|---|---|---|---|
| `GET` | `/health` | — | Liveness probe |
| `GET` | `/ready` | — | Readiness probe (pings Mongo) |
| `GET` | `/metrics` | — | Prometheus exposition format |
| `GET` | `/api/v1/version` | — | Version + service name |
| `GET` | `/api/v1/tickets` | `tickets:read` | List tickets |
| `GET` | `/api/v1/tickets/{id}` | `tickets:read` | Fetch a single ticket |
| `GET` | `/api/v1/projects` | `projects:read` | List projects |
| `GET` | `/api/v1/analytics/summary` | `analytics:read` | SLA + ticket roll-ups |

---

## System endpoints

### `GET /health`

Liveness probe. Always returns HTTP 200 with:

```json
{"ok": true, "version": "0.9.0"}
```

Railway, Kubernetes, and docker-compose probes should hit this — it does
**not** touch Mongo, so it tells you the process is up, not that the
whole stack is healthy.

### `GET /ready`

Readiness probe. Pings Mongo and returns:

```json
{"ok": true, "db": true}
```

If Mongo is unreachable: `{"ok": false, "db": false}` (still HTTP 200 —
check the JSON). Wire this to readiness gates in Kubernetes so traffic
is only routed once the database is available.

### `GET /metrics`

Prometheus text format. Exposes ticket counters, webhook delivery stats,
AI call counters, and HTTP timing histograms. Only mounted when
`METRICS_ENABLED=true`. Protect it behind a network policy / firewall
rule — there is no bearer check.

### `GET /api/v1/version`

```json
{"version": "0.9.0", "name": "XTV-SupportBot"}
```

Useful for deployment smoke tests and for the admin SPA to detect
version mismatches.

---

## Tickets

### `GET /api/v1/tickets`

List tickets, most recent first.

**Scope**: `tickets:read`

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `status` | string | — | Filter by status (`open`, `pending`, `closed`, …) |
| `team_id` | string | — | Filter by routing team |
| `limit` | int | `50` | `1..200` |

**Example**

```bash
curl -sS "$BASE/api/v1/tickets?status=open&limit=20" \
  -H "Authorization: Bearer $XTV_KEY" | jq
```

**Response**

```json
{
  "count": 20,
  "items": [
    {
      "_id": "652f8c1e2a…",
      "user_id": 123456789,
      "project_id": "6501abc…",
      "team_id": "65aa77…",
      "status": "open",
      "priority": "high",
      "tags": ["billing", "vip"],
      "created_at": "2026-04-20T12:34:56Z",
      "closed_at": null,
      "assignee_id": 987654321
    }
  ]
}
```

The projection is intentionally narrow — full ticket bodies, message
history and attachments are **not** returned in the list view. Use the
single-ticket endpoint below when you need them.

### `GET /api/v1/tickets/{id}`

Fetch one ticket by MongoDB ObjectId.

**Scope**: `tickets:read`

**Path parameters**

| Name | Type | Notes |
|---|---|---|
| `id` | string | 24-char hex ObjectId |

**Errors**

| Status | Body | Meaning |
|---|---|---|
| `400` | `{"detail": "bad_id: …"}` | Not a valid ObjectId |
| `404` | `{"detail": "not_found"}` | No ticket with that id |

**Example**

```bash
curl -sS "$BASE/api/v1/tickets/652f8c1e2a7b9c0d1e2f3a4b" \
  -H "Authorization: Bearer $XTV_KEY" | jq
```

**Response** — the full ticket document (fields depend on migrations and
plugins enabled, but always includes `_id`, `status`, `created_at`, and
`messages` if present).

---

## Projects

### `GET /api/v1/projects`

List projects.

**Scope**: `projects:read`

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `active` | bool | — | `true` → only active, `false` → only archived, unset → both |

**Example**

```bash
curl -sS "$BASE/api/v1/projects?active=true" \
  -H "Authorization: Bearer $XTV_KEY" | jq
```

**Response**

```json
{
  "count": 3,
  "items": [
    {
      "_id": "65010abc…",
      "slug": "main",
      "name": "Main Support",
      "active": true,
      "created_at": "2026-01-10T09:00:00Z"
    }
  ]
}
```

---

## Analytics

### `GET /api/v1/analytics/summary`

Roll-up of the last N days.

**Scope**: `analytics:read`

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `days` | int | `7` | `1..365` |

**Example**

```bash
curl -sS "$BASE/api/v1/analytics/summary?days=30" \
  -H "Authorization: Bearer $XTV_KEY" | jq
```

**Response**

```json
{
  "days": 30,
  "tickets": 184,
  "sla_breached": 12,
  "sla_total": 177,
  "sla_compliance_ratio": 0.932,
  "rollups": [
    {"day": "2026-04-23", "total": 9, "sla_breached": 0, "sla_total": 9},
    {"day": "2026-04-22", "total": 7, "sla_breached": 1, "sla_total": 7}
  ]
}
```

`sla_compliance_ratio` is `1 - breached / sla_total`, rounded to three
decimals. `sla_total` excludes tickets that never had an SLA (e.g. those
outside business hours when `FEATURE_BUSINESS_HOURS=true`).

---

## Error model

All errors follow FastAPI's conventions:

```json
{"detail": "…human-readable or structured message…"}
```

Common status codes:

| Status | Meaning |
|---|---|
| `400` | Malformed input (bad id, invalid query param) |
| `401` | Missing or malformed `Authorization` header |
| `403` | Key lacks the required scope; `detail` includes `required` + `granted` |
| `404` | Resource not found |
| `422` | FastAPI validation error (missing query params, wrong type) |
| `503` | Database unavailable (e.g. Mongo down) |

For `403` the response body has extra context:

```json
{
  "detail": {
    "error": "insufficient_scope",
    "required": "analytics:read",
    "granted": ["tickets:read"]
  }
}
```

---

## Rate limiting

`API_RATE_LIMIT_PER_MINUTE` controls a per-key token bucket (default 120).
Exceeding it returns HTTP 429. Set it higher for machine-to-machine
integrations, lower for admin SPA users.

!!! note
    Rate limiting relies on Redis when `REDIS_URL` is set; otherwise it
    falls back to an in-memory limiter that **does not** work across
    multiple replicas. Scaling horizontally requires Redis.

## CORS

`API_CORS_ORIGINS` is a comma-separated list of allowed origins for the
admin SPA. Leave blank to disable cross-origin requests entirely (the
API still works for server-to-server calls and same-origin SPAs).

```env
API_CORS_ORIGINS=https://admin.example.com,https://status.example.com
```

Use `*` **only** for keys that are exclusively `tickets:read` /
`analytics:read` — granting CORS to write scopes is a CSRF risk.

## Versioning

The `/api/v1/…` prefix is stable for the v0.9 series. Breaking changes
will go into `/api/v2/` and overlap for at least one minor release.
Non-versioned endpoints (`/health`, `/ready`, `/metrics`, `/api/v1/version`)
are considered operational and may evolve only additively.

## Further reading

- [Quickstart](api-quickstart.md) — first request in under 5 minutes
- [Authentication](api-auth.md) — key lifecycle, scopes, rotation
- [Write endpoints](api-write.md) — POST routes in Phase 4.7
- [Outgoing webhooks](webhooks.md) — event catalogue + HMAC verification
- [Railway deployment](../ops/railway.md) — public URL walkthrough
