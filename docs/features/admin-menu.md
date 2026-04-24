# Admin menu

The entire admin UX lives behind **one command**: `/admin`.

```
/admin
```

Opens a live dashboard card with eight tabs — Overview · Tickets ·
Teams · Projects · Rules · Broadcasts · Analytics · Settings — laid out
in two rows so the keyboard stays readable on mobile. Every tab
switches in place (same message id) so your DM stays clean.

!!! info "Only one entry point"
    `/panel` was merged into `/admin`. Legacy `/team …`, `/apikey …`,
    `/rules …` and project / broadcast commands still work as
    power-user backups, but are **not** the main way anymore.

## What each tab does

| Tab | Opens |
|---|---|
| **Overview** | Open-ticket / SLA-at-risk / unassigned / active-agent tiles + quick-jump buttons |
| **Tickets** | Today's opened + closed counters + shortcut to the agent cockpit (`/inbox`) |
| **Teams** | Browse list → team detail → Rename / Timezone / Members / Delete |
| **Projects** | Active project count + "Create from template" / "List" / "Blank" |
| **Rules** | Count + New / Browse (full rule builder lives in `/rules` command for now) |
| **Broadcasts** | Start a new broadcast; live progress card |
| **Analytics** | SLA compliance over the last 7d + export / digest buttons |
| **Settings** | Feature-flag grid + 🔑 API keys + 🔒 Rotate secrets |

## Teams — button-driven CRUD

1. Tap the **Teams** tab.
2. Tap **📜 Browse teams** → grid of all teams.
3. Tap a team → detail card with **✏️ Rename · 🌐 Timezone · 👤 Members · 🗑 Delete**.
4. Tap **➕ Add member** in the Members sub-menu → bot asks for the
   user id → you paste it → your reply gets **deleted**, the prompt
   card is **edited into a confirmation**. No new messages, no scroll.

The same pattern — *prompt → type → reply deleted → prompt becomes
confirmation* — applies to **create / rename / timezone / add-member**
everywhere.

## API keys

Gated on `API_ENABLED=true`. Tap **Settings → 🔑 API keys**:

- See every active key with its label, scopes and last-used date.
- **➕ Create key** → prompt asks for
  `<scope[,scope…]> [label]`. On submit, your reply is deleted and
  the plaintext key is shown on the same card exactly once — save it
  immediately.
- **🗑** next to any key → two-step confirm → revoke.

Power-user shortcut still works:

```
/apikey create tickets:read,analytics:read reporting
```

## Chat cleanness

All admin interactions follow the **message-surgery** pattern:

1. Bot asks a question (prompt card, `message_id = P`).
2. You type the answer (`message_id = R`).
3. Bot **deletes R** and **edits P into a result card** — same
   `message_id`, no clutter.

If your input is invalid, the prompt is edited into an error card and
your reply is still deleted; you can try again without scrolling
through the history.

## Cancel anything

`/cancel` in any state aborts the current wizard step and clears the
FSM. The cancel message itself is deleted so the chat stays tidy.
