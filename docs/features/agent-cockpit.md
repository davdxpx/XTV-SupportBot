# Agent cockpit

`/inbox` is the new home screen for agents — a persistent, saved-view
filterable inbox with bulk actions, plus `/note` for internal-only
comments inside ticket topics, plus an auto-rendered customer history.

!!! info "Feature flag"
    Gate on with `FEATURE_AGENT_INBOX=true`. Default is off so the
    legacy `/queue` stays authoritative until teams are briefed.

## `/inbox`

Opens the inbox as a single message with:

- **Saved-view chips** along the top: My open / Unassigned / Overdue /
  High / All open
- **Ticket rows** with a checkbox, priority icon, SLA-at-risk flag,
  unassigned flag, and a trimmed title
- **Bulk-action footer** (shown only when the selection is non-empty):
  Close, Assign me, Priority: High, Priority: Low, Clear selection
- **Pagination** when more than 10 tickets match

Everything is one in-place edit — switching views, toggling a ticket,
paging back and forth never spawns a new message.

### Saved views

| Key | What it shows |
|---|---|
| `my_open` | Tickets assigned to you, status=open (default) |
| `unassigned` | Status=open, no assignee |
| `overdue` | SLA warned or past breach deadline |
| `high_priority` | Priority=high |
| `all_open` | Everything still open |

`by_tag:*`, `by_team:*`, `by_project:*` filters are scaffolded in the
selection state — wiring them to user-editable saved views is a
follow-up.

### Selection state

Your current selection persists in the user FSM, so switching views
or paging preserves what you picked. Clicking **Clear** (or running a
bulk action) empties it.

### Bulk actions

Every bulk action goes through the shared
`xtv_support.services.actions.ActionExecutor`, so:

- One `ActionExecuted` event per ticket per action (audit-log friendly)
- `BulkActionStarted` / `BulkActionCompleted` wrap the run
- Failures don't abort the batch — you get a count back
  (`Bulk close: 4 ok, 1 failed`)

## `/note <text>`

Inside a ticket topic thread, appends an internal note to the ticket's
`internal_notes` field. Notes:

- Are **never** forwarded to the customer
- Live in a separate field from the public `history` so no future
  "history forwarder" can leak them
- Fire the same `ActionExecuted(action="add_internal_note")` event as
  the API + bulk path
- Show up on the ticket header re-render as a collapsible section

Example:

```
/note customer escalated via email as well; see thread
```

Returns:

```
📝 Internal note added (3 total — hidden from the customer).
```

## Customer history card

When a new topic is created for a user with a history
(`FEATURE_CUSTOMER_HISTORY_PIN=true`, default on), a short card gets
pinned at the top of the thread:

```
👤 Customer history — Ada
ID 42

💎 VIP

7 tickets total (6 closed) · ⭐ 4.8 CSAT avg · ⏱ 12m first response

Last tickets
• [closed] Refund issue
• [open] Password reset
```

The renderer is pure — you can reuse it from the API or plugins via
`xtv_support.ui.templates.agent_inbox.render_customer_history`.

## Quick-reply menu (coming)

Plan 4.5 also sketches a button-driven macro picker with preview +
edit-before-send. The repo helper
`services/macros/service.list_for_agent` is in place; the inline-menu
wiring lands in a follow-up commit.

## Audit story

Because the cockpit uses `ActionExecutor` with `origin="bulk"` (for
/inbox) or `origin="bot"` (for `/note`), every write is attributable.
Run:

```
/rules                        # ... or audit-log queries
```

and you see exactly who did what and from which surface.

## Known gaps (scheduled)

- Custom user-defined saved views (`by_tag`, `by_team`, etc.)
- "Next unread ticket" queue walker
- Quick-reply menu in topics
- Typing indicators / read receipts forwarded
