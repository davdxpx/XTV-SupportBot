# REST API

FastAPI app mounted when `API_ENABLED=true`. OpenAPI schema served at
`/api/v1/openapi.json`, interactive docs at `/api/v1/docs`.

## Authentication

Every endpoint (except `/health`, `/ready`, `/metrics`) expects
`Authorization: Bearer <key>`. Keys are created with `/apikey create`
inside the bot admin DM; plaintext is shown exactly once.

## Scopes

| Scope | Grants |
|---|---|
| `tickets:read` | `GET /api/v1/tickets…` |
| `tickets:write` | write endpoints (reply / close) — future |
| `projects:read` | `GET /api/v1/projects…` |
| `projects:write` | create/update — future |
| `users:read` | `GET /api/v1/users…` — future |
| `analytics:read` | `GET /api/v1/analytics/summary` |
| `webhooks:write` | register / revoke webhooks — future |
| `admin:full` | everything |

## Endpoints in v0.9.0

| Method | Path | Scope |
|---|---|---|
| GET | `/health` | — |
| GET | `/ready` | — |
| GET | `/metrics` | — (firewall-gated) |
| GET | `/api/v1/version` | — |
| GET | `/api/v1/tickets?status=&team_id=&limit=` | `tickets:read` |
| GET | `/api/v1/tickets/{id}` | `tickets:read` |
| GET | `/api/v1/projects?active=` | `projects:read` |
| GET | `/api/v1/analytics/summary?days=` | `analytics:read` |
