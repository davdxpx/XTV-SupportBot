# ActionExecutor

One execution path for every ticket mutation — bot UI, bulk actions in
the agent cockpit, automation rules, REST API writes. Introduced in
Phase 4.1 as the foundation every subsequent phase builds on.

## Why one executor

Before the overhaul, each surface (handler, API, rule) implemented its
own "close ticket" / "assign" / "tag" logic. That meant three different
events (or none), three different audit trails, three different error
codes for the same logical error. Consolidating into one executor
means:

- Every mutation publishes the same `ActionExecuted` /
  `ActionFailed` event with an `origin` attribute
  (`bot | api | rule | bulk`)
- Audit logs line up
- Analytics can group by origin for attribution
- Plugins subscribing to `ActionExecuted` work across every surface

## Built-in actions

Registered in `xtv_support.services.actions.default_registry` at import
time:

| Action | Params |
|---|---|
| `assign` | `{"assignee_id": int \| null}` |
| `tag` / `untag` | `{"tag": str}` |
| `set_priority` | `{"priority": "low" \| "normal" \| "high"}` |
| `close` | `{"reason": str}` |
| `reopen` | `{}` |
| `add_internal_note` | `{"text": str}` |

## Running an action

```python
from xtv_support.services.actions import ActionContext, ActionExecutor

executor = ActionExecutor()                    # uses default_registry
ctx = ActionContext(
    db=db,
    bus=bus,
    client=client,                             # optional; some actions need it
    actor_id=user_id,
    origin="bot",                              # "bot" | "api" | "rule" | "bulk"
)
result = await executor.execute(
    ctx,
    "close",
    ticket_id="652…",
    params={"reason": "resolved"},
)

if not result.ok:
    log.warning("close.failed", detail=result.detail)
```

`ActionResult` has `ok: bool`, `detail: str | None`, `data: dict`.

## Registering a custom action

Write a small class that implements the `Action` protocol:

```python
from xtv_support.services.actions import Action, ActionContext, ActionResult
from xtv_support.services.actions.registry import default_registry


class _EmojiReactAction:
    name = "emoji_react"

    async def execute(
        self,
        ctx: ActionContext,
        *,
        ticket: dict | None,
        params: dict,
    ) -> ActionResult:
        if ticket is None or ctx.client is None:
            return ActionResult(ok=False, detail="ticket_or_client_required")
        emoji = params.get("emoji") or "👍"
        # … call pyrogram here to add the reaction …
        return ActionResult(ok=True, data={"emoji": emoji})


default_registry.register(_EmojiReactAction())
```

Once registered, the action is instantly available:

- from bulk-action callbacks (if you add a button to the cockpit)
- from the rules engine (`{"name": "emoji_react", ...}` in a rule's
  `actions`)
- from the REST API (`POST /api/v1/tickets/{id}/bulk-action` with
  `{"action": "emoji_react", "params": {"emoji": "🔥"}}`)

No executor change required.

## Events

`ActionExecuted`:

| Field | Notes |
|---|---|
| `action` | name registered in the registry |
| `ticket_id` | `None` for global actions |
| `actor_id` | who caused it (admin id, API-key creator, `None` for rules) |
| `origin` | `"bot" \| "api" \| "rule" \| "bulk"` |
| `params` | the params dict passed in |
| `latency_ms` | end-to-end duration |

`ActionFailed` mirrors the shape plus an `error` string. Both are
published on the `EventBus` and re-exported via the outgoing-webhook
bridge if configured.

## Ordering guarantees

Within one `execute()` call actions are atomic as far as the
application is concerned — `ActionExecuted` is only emitted after the
underlying coroutine returns successfully. Between calls the caller
is responsible for ordering (`asyncio.gather` is allowed; they still
each emit their own event).

## Testing

`ActionExecutor` runs fine against a mocked Mongo + a mocked bus —
patch `_tickets_repo` / `_notes_repo` accessors to return fakes,
build a synchronous bus that appends to a list, assert on the list.

See `tests/unit/services/actions/test_executor.py` for the canonical
pattern.
