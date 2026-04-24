# API write endpoints

Phase 4.7 opens up the bot to programmatic mutation. Every write route
is dispatched through the same `ActionExecutor` as bot-UI and rule-engine
writes, so one audit trail / event surface covers all origins.

`$BASE` is your public URL — `https://xtvsupport.up.railway.app` on
Railway.

## Tickets

### `POST /api/v1/tickets/{id}/close`

**Scope:** `tickets:write`

```json
{"reason": "resolved"}
```

Response:

```json
{"ok": true, "action": "close", "data": {"reason": "resolved"}}
```

Errors:
- `400 {"detail": "ticket_not_found"}`
- `400 {"detail": "bad_id: …"}`

### `POST /api/v1/tickets/{id}/reopen`

**Scope:** `tickets:write`

```json
{"reason": "customer followed up"}
```

### `POST /api/v1/tickets/{id}/assign`

**Scope:** `tickets:write`

```json
{"assignee_id": 123456789}   // null → unassign
```

### `POST /api/v1/tickets/{id}/tags`

**Scope:** `tickets:write`. Replacement semantics — the body *is* the
new tag list. The route computes the diff and emits per-tag
`tag` / `untag` `ActionExecuted` events.

```json
{"tags": ["billing", "vip"]}
```

Response:

```json
{"ok": true, "added": ["vip"], "removed": ["old_tag"]}
```

### `POST /api/v1/tickets/{id}/priority`

**Scope:** `tickets:write`

```json
{"priority": "high"}   // low | normal | high
```

### `POST /api/v1/tickets/{id}/notes`

**Scope:** `tickets:write`. Appends an *internal* note — never
forwarded to the customer, stored in `tickets.internal_notes` (separate
from the public history array).

```json
{"text": "customer is a VIP, preferred channel is email"}
```

### `POST /api/v1/tickets/{id}/bulk-action`

**Scope:** `tickets:write`. Thin passthrough to any action registered
in the executor. Use this for actions without a dedicated route or
for future actions that plugins register.

```json
{"action": "emoji_react", "params": {"emoji": "🔥"}}
```

## Projects

### `POST /api/v1/projects`

**Scope:** `projects:write`

Create from a built-in template (see
[project templates](../features/project-templates.md)):

```json
{
  "project_slug": "pay",
  "name": "Payments Support",
  "template_slug": "billing"
}
```

Response:

```json
{
  "ok": true,
  "project_id": "652…",
  "template_slug": "billing",
  "macros_seeded": 3,
  "kb_articles_seeded": 2,
  "routing_rules_seeded": 3
}
```

Or create a blank project by omitting `template_slug`.

Errors:
- `409 {"detail": "project_slug_taken"}`
- `400 {"detail": "unknown_template: …"}`

### `DELETE /api/v1/projects/{slug}`

**Scope:** `projects:write`. Soft-archive (`active=false`,
`archived_at` set). Existing tickets keep their backreference; new
tickets cannot be opened against an archived project.

## Webhooks

Full subscription CRUD. Secrets are returned **once** on create.

### `GET /api/v1/webhooks`

**Scope:** `webhooks:write`. Lists all subscriptions (active + revoked)
without secrets.

### `POST /api/v1/webhooks`

**Scope:** `webhooks:write`

```json
{
  "url": "https://example.com/hook",
  "events": ["ticket.closed", "ticket.sla_breached"],
  "label": "PagerDuty on breach"
}
```

Response:

```json
{
  "id": "652…",
  "secret": "xtvwh_<40-char-one-time>",
  "url": "https://example.com/hook",
  "events": ["ticket.closed", "ticket.sla_breached"]
}
```

The `secret` is shown exactly once — store it to verify future
deliveries (see [webhooks](webhooks.md)).

Pass an empty `events` array to receive **every** event.

### `DELETE /api/v1/webhooks/{id}`

**Scope:** `webhooks:write`. Marks the subscription `revoked_at=now`;
future deliveries are skipped.

## One execution path

All the ticket routes above go through
`xtv_support.services.actions.ActionExecutor` with `origin="api"`.
That means:

- The same `ActionExecuted` / `ActionFailed` events fire regardless of
  whether the close button was pressed in Telegram, the API, or
  triggered by a rule.
- Audit-log entries have a consistent shape.
- Analytics queries group by `origin` for attribution
  (`bot | api | rule | bulk`).
- Plugins that subscribe to `ActionExecuted` work with every path
  automatically.

## Reading actions

`GET /api/v1/rules` and `GET /api/v1/rules/{id}` (scope `rules:read`)
let you inspect the automation rules that might run alongside any
write. See [automation rules](../features/automation-rules.md).
