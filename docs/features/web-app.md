# Web App (Admin SPA + Telegram Mini-App)

Since v0.10 XTV-SupportBot ships a React Single-Page App that is
served directly from the FastAPI process. It powers two surfaces
from the same bundle:

1. **Admin console** — open `https://<your-domain>/` in a regular
   browser, paste an `xtv_…` API key, and get a full operations UI
   (Overview / Inbox / Ticket detail / Projects / Rules).
2. **Telegram Mini-App** — opened by tapping an **Open App** inline
   button or the menu-button in any chat. The page authenticates
   against Telegram's signed `initData`, so the user is logged in
   automatically and scoped to their own tickets.

The `UI_MODE` environment variable picks which entry points the bot
exposes: classic inline buttons (`chat`), Mini-App only (`webapp`),
or both side-by-side (`hybrid`).

## Architecture at a glance

```
                                ┌──────────────────────────────┐
            HTTPS request ─────▶│ FastAPI (uvicorn, same PID   │
                                │ as the Telegram bot)         │
                                │                              │
                                │  /api/v1/*   ← JSON          │
                                │  /assets/*   ← SPA bundle    │
                                │  /          ← index.html     │
                                │  /<any>     ← index.html     │
                                │               (SPA fallback) │
                                └──────────────────────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────────┐
                                │ React SPA (/web/)            │
                                │                              │
                                │  desktop browser → Admin UI  │
                                │  in Telegram      → User UI  │
                                └──────────────────────────────┘
```

* **One process, one port.** Railway / Render / Fly inject `$PORT`
  which the bot picks up via `effective_api_port`; the SPA lives at
  the same origin as the JSON API so CORS is a non-issue.
* **One bundle, two UIs.** `main.tsx` asks `GET /api/v1/me` on the
  first render; if the caller is an admin on desktop it mounts the
  full `AdminLayout`, otherwise it mounts the Mini-App-friendly
  `UserLayout` with a bottom tab-bar.

## Modes

`UI_MODE` in `.env`:

| Mode | Inline buttons | Open-App button | When to pick |
|---|---|---|---|
| `chat` *(default)* | ✅ | — | You don't want to publish a Mini-App. 100% backward-compatible. |
| `webapp` | — | ✅ | Clean one-button UX. Every interaction happens inside the SPA. |
| `hybrid` | ✅ | ✅ | Transitioning from `chat` → `webapp`; lets users choose per tap. |

Per-user override: `users.ui_pref` (`chat` / `webapp` / `hybrid`)
beats the global. Set it from the Mini-App's **Settings → UI
preference** screen.

### Graceful fallback

Even in `webapp` / `hybrid` mode the bot downgrades to `chat`
silently when:

* `WEBAPP_URL` is empty or not `https://`
* the user's Telegram client is `< 6.0` (WebApps shipped April 2022)
* a Mongo hiccup prevents the user-pref lookup

So a misconfigured deploy never emits a broken keyboard.

## Authentication

### Desktop admin
`Authorization: Bearer xtv_<40-char-key>`. Keys are created via
`/apikey create admin:full` in the bot and persisted SHA-256 at
rest; plaintext is shown **once**. See
[API auth](../reference/api-auth.md) for the full key lifecycle.

### Telegram Mini-App
`X-Telegram-Init-Data: user=%7B...%7D&auth_date=…&hash=…`

The `initData` query string is signed with
`HMAC-SHA256(key="WebAppData", msg=BOT_TOKEN)`. The server
validates the signature, rejects `auth_date` older than 24 hours,
and decodes the `user` JSON into a typed `TelegramUser`. See
`src/xtv_support/api/auth_webapp.py` for the implementation.

The shared FastAPI dependency `current_tg_user_or_apikey` picks
whichever is present: `initData` wins if both are on the request.

## `/api/v1/me` — user-scoped endpoints

Every route below is scoped to **the caller** — a user can never
read or mutate another user's ticket.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/me` | Profile, `is_admin`, `ui_mode`, brand strings |
| `GET` | `/api/v1/me/projects` | Active projects available for intake |
| `GET` | `/api/v1/me/tickets?status=…` | Caller's tickets with filter |
| `GET` | `/api/v1/me/tickets/{id}` | Ticket + history (internal notes stripped) |
| `POST` | `/api/v1/me/tickets` | Create a new ticket |
| `POST` | `/api/v1/me/tickets/{id}/reply` | Add a user reply |
| `POST` | `/api/v1/me/tickets/{id}/close` | Self-close |
| `GET` | `/api/v1/me/settings` | Language + notification prefs + `ui_pref` |
| `PATCH` | `/api/v1/me/settings` | Partial update |

Admin routes (`/api/v1/tickets`, `/projects`, `/rules`, `/analytics`,
`/webhooks`) keep their existing API-key + scope model — see
[API reference](../reference/api.md).

## SPA routes

Every path is served by `index.html` so deep-links survive a hard
refresh.

### User
- `/` — Home (greeting, stats, quick actions)
- `/new` — New ticket (project picker + message)
- `/tickets` — My tickets (filter chips)
- `/tickets/:id` — Chat-style thread, reply, self-close
- `/settings` — Language / notifications / UI preference

### Admin
- `/admin` — Overview tiles
- `/admin/inbox` — Saved-view chips + ticket table
- `/admin/tickets/:id` — Thread + tag editor + reply / close / reopen
- `/admin/projects` — List + create-from-template dialog
- `/admin/rules` — Full rule builder (create / edit / toggle / delete)

## Enabling the Mini-App

1. Deploy with `UI_MODE=webapp` (or `hybrid`) and a valid
   `WEBAPP_URL=https://<your-domain>/`.
2. Configure the WebApp domain in **@BotFather → Bot Settings →
   Configure Mini App** and point it at the same URL.
3. Optional: set `WEBAPP_SET_MENU_BUTTON=true` so the bot calls
   `setChatMenuButton` at boot and every chat gets a persistent
   "Open App" button next to the text composer.

See [Deploy the Web App](../ops/deploy-webapp.md) for the full
Railway walkthrough.

## Rolling back

* Instantly disable the Mini-App: `UI_MODE=chat` + redeploy.
* Disable the SPA mount but keep the API: `WEB_ENABLED=false`.
* Nothing to undo on the DB — there are no Mini-App-specific
  collections or migrations.
