# User experience

The v0.9 pre-release adds a proper home screen for end users, a pure
browse-only help center, and per-user notification preferences.

!!! info "No flag needed"
    The onboarding panel is the **default** for `/start` — no feature
    flag. Deep-link payloads on `/start` (contact links, project-slug
    deep links) keep their legacy fast path; only the no-payload call
    renders the panel. `/home` is an alias of `/start`, `/faq` and
    `/settings` are always available.

## `/home` — the onboarding panel

The user's home screen inside the bot. Four primary buttons:

```
📮 New ticket          📚 Browse help
🗂 My tickets (N new)   ⚙️ Settings
```

- **New ticket** opens the existing KB-gate-then-intake flow.
- **Browse help** is a pure read-only KB search (see `/faq` below) —
  users can skim articles without opening a ticket.
- **My tickets** badges the unread count (tickets with an admin reply
  newer than the user's last read).
- **Settings** opens the preferences panel.

A stats line shows "X open · Y closed this month" when the user has
any history.

If the admin has pinned an announcement, it appears as a strip
beneath the greeting.

## `/faq` — help center

Pure browse mode over the existing knowledge base. No ticket gets
opened; users can leave via the back button any time.

Shows paginated article cards with title + 120-char preview. Search
by running `/faq <keyword>` or tapping 🔍 Search from the home panel.

## `/settings`

Per-user preferences:

- **Language** (`/lang` from here; auto-detected on first run via
  Telegram's `language_code`)
- **Notify on reply** — receive a DM when an agent replies
- **CSAT after close** — show the 1–5★ survey after close
- **Announcements** — receive admin-pinned announcements
- **Export my data** / **Delete my data** — GDPR shortcuts

Toggles persist to `users.notification_prefs`.

## Boot migration

Phase 4.3's migration (SCHEMA_VERSION → 9) adds two fields to every
user document idempotently:

- `notification_prefs: {notify_reply: true, notify_csat: true,
  notify_announcements: true}`
- `onboarding_shown_at: null`

## Deep-link fast path

`/start` still handles two legacy deep-link payloads **before** the
onboarding panel is rendered, so existing links keep working:

- `t.me/YourBot?start=contact_<uuid>` — jumps straight into a
  contact-form flow (the user is set to `AWAITING_CONTACT_MSG`).
- `t.me/YourBot?start=<project_slug>` — jumps into that project's
  intake flow (`AWAITING_FEEDBACK`).

Only `/start` without a payload (and `/home`) renders the onboarding
panel.

## Panel architecture

All three screens use the shared
`xtv_support.ui.primitives.panel.Panel` — a dashboard layout with
optional tabs, stat tiles, action rows, and pagination. The same
primitive powers `/admin` (admin control panel) and `/inbox` (agent
cockpit), so muscle memory transfers.

Renderers are pure — lifted out into
`xtv_support.ui.templates.onboarding_panel` so tests can assert on
text output without needing a pyrogram client.

## Known gaps (scheduled)

- Per-ticket read-cursor (today the "N new" badge uses
  `last_admin_msg_at > last_user_msg_at`)
- Rich intake forms driven by `template.intake_fields` (dynamic prompt
  sequence instead of free-form first message)
- "Continue where you left off" recovery for dropped multi-step flows
