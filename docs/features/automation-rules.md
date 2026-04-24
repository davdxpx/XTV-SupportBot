# Automation rules

If/then pipelines that react to ticket-lifecycle events. Built on the
same `ActionExecutor` as bot-UI and API writes — one audit trail,
one event surface.

## Model

A **rule** is:

- `name` — human label
- `trigger` — one event class name (`TicketCreated`, `TicketTagged`,
  `SlaBreached`, …)
- `conditions` — list of predicates AND-joined
- `actions` — list of `ActionRef` run sequentially
- `cooldown_s` — don't re-fire on the same ticket within N seconds
- `enabled` — off by default until you flip it

## Supported triggers

| Trigger | When |
|---|---|
| `TicketCreated` | New ticket |
| `TicketAssigned` | Assignment changed (incl. to `null`) |
| `TicketTagged` | Tag added / removed |
| `TicketPriorityChanged` | Priority changed |
| `TicketClosed` | Closed |
| `TicketReopened` | Reopened |
| `SlaWarned` | SLA warn-threshold crossed |
| `SlaBreached` | SLA breach-threshold crossed |

## Condition operators

Conditions are pure predicates over the ticket document. Available
ops:

| Op | Meaning |
|---|---|
| `eq` / `ne` | Equals / not equals |
| `in` / `not_in` | Value is / isn't in a given list |
| `contains` | List field contains value (e.g. `tags contains billing`) |
| `gt` / `lt` | Numeric greater-than / less-than |

`field` supports dotted paths (`meta.lang`).

## Action catalogue

Every built-in action from the `ActionExecutor` registry is available:

| Action | `params` shape |
|---|---|
| `assign` | `{"assignee_id": 123}` — `null` to unassign |
| `tag` | `{"tag": "billing"}` |
| `untag` | `{"tag": "billing"}` |
| `set_priority` | `{"priority": "high"}` |
| `close` | `{"reason": "auto_resolved"}` |
| `reopen` | `{}` |
| `add_internal_note` | `{"text": "Billing VIP — auto-escalated"}` |

Plugins can register more; `/rule_new` accepts any name from the
registry.

## Worked example — billing auto-escalate

"When a ticket is created, tagged billing, priority high, assign the
billing team and drop an internal note."

```
/rule_new "Billing auto-escalate" TicketCreated \
  {"conditions":[
     {"field":"priority","op":"eq","value":"high"},
     {"field":"tags","op":"contains","value":"billing"}
   ],
   "actions":[
     {"name":"assign","params":{"assignee_id":123456}},
     {"name":"add_internal_note","params":{"text":"Auto-routed to billing team"}}
   ],
   "cooldown_s": 0}
```

The bot replies with the new rule ID (disabled). Enable it:

```
/rule_enable <rule_id>
```

## Dry-run

```
/rule_test <rule_id> <ticket_id>
```

Evaluates conditions without executing, returns per-condition
pass/fail:

```
Dry-run: ✅ WOULD FIRE
  ✅ priority eq 'high'
  ✅ tags contains 'billing'
```

## Cooldowns + caps

`cooldown_s` is per-rule, per-ticket. A rule that fires on
`SlaWarned` with a 30-minute cooldown won't re-fire for the same
ticket if it crosses the warn threshold again within the window (it
publishes `RuleSkipped(reason="cooldown")` instead).

`max_fires_per_day` is in the model but not enforced yet — the
implementation lands in a follow-up once we have enough in-the-wild
signal on what the right default is.

## Events

Every rule execution emits exactly one `RuleExecuted` or
`RuleSkipped` event. Consume via the in-process event bus or via
outgoing webhooks (`rule.executed`):

```json
{
  "event": "rule.executed",
  "rule_id": "…",
  "ticket_id": "…",
  "trigger": "TicketCreated",
  "actions_succeeded": 2,
  "actions_failed": 0,
  "latency_ms": 34
}
```

## Versioning + audit

Every rule save bumps `version`; the previous payload is pushed to
`history` on the document so ops can audit "who changed this, when,
why" after the fact.

## Web admin (primary UI)

The **/admin/rules** page in the SPA has a full builder modal:
name, trigger dropdown, add/remove conditions (field + op + value),
add/remove actions (name + JSON params), cooldown seconds, enabled
toggle. Each rule card has Enable / Disable / Delete buttons.

## Admin commands reference (Telegram bot)

| Command | Purpose |
|---|---|
| `/rules` | List rules |
| `/rule_new "name" <trigger> <JSON>` | Create (disabled) |
| `/rule_enable <id>` | Enable |
| `/rule_disable <id>` | Disable |
| `/rule_delete <id>` | Delete |
| `/rule_test <rule_id> <ticket_id>` | Dry-run |

## API

| Method | Path | Scope |
|---|---|---|
| `GET` | `/api/v1/rules` | `rules:read` |
| `GET` | `/api/v1/rules/{id}` | `rules:read` |
| `POST` | `/api/v1/rules` | `rules:write` |
| `PATCH` | `/api/v1/rules/{id}/enabled` | `rules:write` |
| `DELETE` | `/api/v1/rules/{id}` | `rules:write` |

See [API write reference](../reference/api-write.md#automation-rules)
for request/response schemas.

## Design notes

- Conditions are **pure** — evaluation is side-effect free, so
  dry-run and production use share code.
- Actions are **sequential** — order in the `actions` array is the
  order they run. This matters for things like
  `set_priority → tag → close`.
- Failures are **isolated** — one failed action doesn't abort the
  batch; `actions_failed > 0` in `RuleExecuted` surfaces partial
  success.
- The evaluator attaches at **boot**, not on first event — so a
  restart doesn't drop any rules that should fire on the next event.
