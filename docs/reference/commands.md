# Command reference

Every Telegram command the bot recognises, grouped by where it runs.
Commands are **power-user shortcuts** — the menu-first UX (`/start` for
users, `/admin` for admins) is the recommended path. Commands stay
available for automation, scripting, and keyboard-driven workflow.

Each row is **verified against the code** as of the current `main`
branch. If a command isn't listed here, it isn't wired up — please
open an issue before relying on it.

## How each surface is gated

| Surface | Who sees it | Chat context |
|---|---|---|
| **User DM** | anyone who started the bot | private chat with the bot |
| **Admin DM** | users whose Telegram id is in `ADMIN_IDS` | private chat with the bot |
| **Agent DM** | users with `Role.AGENT`+ in RBAC | private chat with the bot |
| **Topic** | admins / agents in the forum supergroup | inside a ticket's topic thread |

---

## User DM

| Command | Arguments | What it does | Menu equivalent |
|---|---|---|---|
| `/start` | optional deep-link payload (`contact_<uuid>` or project slug) | Opens the onboarding panel; deep-link payloads enter the contact/project flow directly. | — |
| `/home` | — | Alias of `/start` without payload. | — |
| `/faq` | — | Pure read-only KB browse. | `/start` → 📚 Browse help |
| `/settings` | — | Language + notification preference panel. | `/start` → ⚙️ Settings |
| `/tickets` | — | Paginated list of your own tickets. | `/start` → 🗂 My tickets |
| `/close` | — | Close the ticket you have open. | ticket card → Close button |
| `/lang` | — | Change your UI language. | `/settings` → 🌐 Change language |
| `/humanplease` | — | Escape the KB gate when it loops on you. | — |
| `/gdpr_export` | — | Sends your full data export as a JSON document. | `/settings` → 📥 Export my data |
| `/gdpr_delete` | — | Two-step deletion with 30-day grace window. | `/settings` → 🗑 Delete my data |

## Admin DM

All require your Telegram id to appear in `ADMIN_IDS`. Some additionally
require a RBAC role; noted per row.

### Dashboard / navigation

| Command | Arguments | What it does |
|---|---|---|
| `/admin` | — | Opens the tabbed control panel (Overview / Tickets / Teams / Projects / Rules / Broadcasts / Analytics / Settings). |
| `/panel` | — | Alias of `/admin`. |
| `/history` | `<user_id>` | Last 10 tickets for a given user. |

### API keys — `Role.ADMIN`

Gated on `API_ENABLED=true`. Menu equivalent: `/admin` → Settings → 🔑 API keys.

| Command | Arguments | What it does |
|---|---|---|
| `/apikey` | — | Opens the API-key management card. |
| `/apikey list` | — | Same as the card in text form. |
| `/apikey create` | `<scope[,scope…]>` `[label]` | Mint a key. Plaintext is shown **once**. |
| `/apikey revoke` | `<key_id>` | Invalidate a key immediately. |

Available scopes: `tickets:read`, `tickets:write`, `projects:read`,
`projects:write`, `users:read`, `analytics:read`, `webhooks:write`,
`rules:read`, `admin:full`. See [API authentication](api-auth.md).

### Teams — `Role.SUPERVISOR`

Menu equivalent: `/admin` → Teams tab.

| Command | Arguments | What it does |
|---|---|---|
| `/team list` | — | Tabular list with member counts, tz and rule counts. |
| `/team create` | `<slug>` `<name…>` | Create a team. |
| `/team rename` | `<slug>` `<new_name…>` | Change display name. |
| `/team delete` | `<slug>` | Remove a team (keeps member accounts). |
| `/team tz` | `<slug>` `<IANA_tz>` | Set timezone (`Europe/Berlin`, `UTC`, …). |
| `/team members` | `<slug>` | List member ids. |
| `/team addmember` | `<slug>` `<user_id>` | Add a Telegram user id to the team. |
| `/team removemember` | `<slug>` `<user_id>` | Remove a Telegram user id. |

### Roles (RBAC) — `Role.OWNER`

Menu equivalent: none yet — the roles menu lands in a later release.

| Command | Arguments | What it does |
|---|---|---|
| `/role list` | — | Show every user with an assigned role. |
| `/role grant` | `<user_id>` `<role>` | Grant a role (`admin` / `supervisor` / `agent` / `viewer`). |
| `/role revoke` | `<user_id>` | Drop a user's role. |

### Project templates — `Role.ADMIN`

Menu equivalent: `/admin` → Projects → 📁 Create from template.

| Command | Arguments | What it does |
|---|---|---|
| `/templates` | — | List available project templates. |
| `/project_template` | `<template_slug>` `<project_slug>` `[name…]` | Create a project from a built-in template. |

Built-in templates: `support`, `feedback`, `contact`, `billing`,
`dev_github`, `vip`, `community`. See
[project templates](../features/project-templates.md).

### Automation rules — `Role.ADMIN`

Menu equivalent: `/admin` → Rules tab (read/listing only; full builder
lives in the commands for now).

| Command | Arguments | What it does |
|---|---|---|
| `/rules` | — | List all automation rules. |
| `/rule_new` | `"<name>"` `<trigger>` `<JSON>` | Create a rule (disabled until enabled). See example below. |
| `/rule_enable` | `<id>` | Enable a rule. |
| `/rule_disable` | `<id>` | Disable a rule. |
| `/rule_delete` | `<id>` | Delete a rule. |
| `/rule_test` | `<rule_id>` `<ticket_id>` | Dry-run conditions (no actions executed). |

Example `/rule_new` body:

```
/rule_new "Billing fast-track" TicketCreated {"conditions":[{"field":"priority","op":"eq","value":"high"},{"field":"tags","op":"contains","value":"billing"}],"actions":[{"name":"assign","params":{"assignee_id":123456}},{"name":"add_internal_note","params":{"text":"auto-routed"}}],"cooldown_s":0}
```

See [automation rules](../features/automation-rules.md) for trigger,
operator and action tables.

### Knowledge base — `Role.ADMIN`

| Command | Arguments | What it does |
|---|---|---|
| `/kb` | — | Opens the KB management card (list / add / edit / delete). |

See [macros & KB](../features/macros-and-kb.md).

## Agent DM

All require `Role.AGENT` or above.

| Command | Arguments | What it does |
|---|---|---|
| `/queue` | — | Open tickets routed to any team you belong to. |
| `/mytickets` | — | Tickets currently assigned to you. |
| `/inbox` | — | Agent cockpit with saved views + bulk actions. Gated on `FEATURE_AGENT_INBOX=true`. |

## Topic (inside the admin forum supergroup)

These only run inside a ticket's topic thread — pyrogram routes them
via `is_admin_forum_topic`. Any non-command text posted in a topic is
forwarded to the user as an admin reply.

| Command | Arguments | What it does |
|---|---|---|
| `/close` | — | Close the ticket, notify the user, optionally prompt CSAT. |
| `/assign` | `<user_id \| me \| none>` | Assign / unassign the agent. |
| `/tag add` | `<name>` | Add a tag. |
| `/tag rm` | `<name>` | Remove a tag. |
| `/macro save` | `<name>` `<text…>` | Save a macro the team can reuse. |
| `/macro use` | `<name>` | Send a macro (placeholder substitution on `{user_name}`). |
| `/macro list` | — | Show all macros. |
| `/macro show` | `<name>` | Reveal the raw body of a macro. |
| `/macro del` | `<name>` | Delete a macro. |
| `/note` | `<text…>` | Internal note, hidden from the user, stored on `tickets.internal_notes`. |
| `/draft` | — | Generate an AI reply draft. Gated on `FEATURE_AI_DRAFTS=true`. |

## Universal

| Command | Context | What it does |
|---|---|---|
| `/cancel` | any FSM-armed state | Abort the current wizard step, clear FSM data, and (for chat-clean surgery flows) delete the cancel message to keep the chat tidy. |

## What's **not** a command

A handful of surfaces look like they should be commands but are
callback-only:

- Projects CRUD — everything happens through `/admin` → Projects tab
  callbacks. There is no `/project` command.
- Broadcasts — started via the admin-dashboard "Broadcast" button.
  There is no `/broadcast` command.
- User block / unblock — admin dashboard callbacks.
- Tag global CRUD — same. The topic-level `/tag add|rm` is separate
  and does exist.

## Versions

All of the above is verified against code on `main`. This page is
kept in sync with pull-request review; if you spot a drift, open an
issue.
