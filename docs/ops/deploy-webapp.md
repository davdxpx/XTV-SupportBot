# Deploy the Web App on Railway

This walkthrough assumes you already have the bot running on Railway
per the [Railway guide](railway.md). It covers:

1. Making the bundled React SPA load when a user visits your Railway
   URL (works even in `UI_MODE=chat`).
2. Turning on the Telegram Mini-App so users tap **Open App** and
   handle tickets without inline buttons.

## 1. Serve the admin SPA

### a. Build pipeline
The default `nixpacks.toml` installs Node.js 20 alongside Python and
runs `cd web && npm ci && npm run build`. No extra config needed.

If you need to disable the mount (e.g. you serve the SPA from a
separate service), set:

```env
WEB_ENABLED=false
```

### b. What lives where
| URL | Served by |
|---|---|
| `/` | React SPA (`index.html`) |
| `/assets/*` | SPA bundle (JS/CSS, long-cached) |
| `/<any-other-path>` | SPA fallback (`index.html`) — so React-Router deep-links survive a refresh |
| `/api/v1/*` | JSON API |
| `/health`, `/ready` | JSON probes |

### c. Verify
```bash
curl -I https://<your-domain>/
# → HTTP/2 200, content-type: text/html

curl -sS https://<your-domain>/api/v1/version
# → {"version":"…","name":"XTV-SupportBot"}
```

### d. First login
1. In the bot, run `/apikey create admin:full`. Copy the `xtv_…`
   string (shown **once**).
2. Open `https://<your-domain>/` in your browser, paste the key,
   sign in. You land on the Overview tab.

## 2. Turn on the Mini-App (optional)

### a. Environment
```env
UI_MODE=webapp                                   # or hybrid
WEBAPP_URL=https://<your-domain>/
WEBAPP_SET_MENU_BUTTON=true                      # adds global Open-App button
WEBAPP_MENU_BUTTON_TEXT=Open App
```

HTTPS is mandatory — Telegram refuses plain-HTTP WebApps. Railway's
default `*.up.railway.app` subdomain already has a valid cert.

### b. Register the WebApp with BotFather
Telegram requires the WebApp domain to be declared explicitly:

1. DM **@BotFather**.
2. `/mybots` → your bot → **Bot Settings** → **Configure Mini App**
   → **Enable Mini App** → paste your `https://…` URL.
3. Optional but recommended: **Configure Mini App** → **Short
   Description** / **Photo** — these are shown in the launch
   animation.

> If you skip this step, the bot will still try to send
> `web_app` buttons but Telegram clients will render them as
> ungoverned inline buttons or nothing at all.

### c. Menu button
`WEBAPP_SET_MENU_BUTTON=true` makes the bot call `setChatMenuButton`
at boot, adding a persistent button next to the composer in every
chat. The call is logged with:

```
boot.webapp_menu_set url=https://… text="Open App"
```

If it logs `boot.webapp_menu_failed` check that step 2b was done —
the API rejects menu-button URLs that don't match a registered Mini
App.

### d. Verify end-to-end
1. Send `/start` to your bot.
2. The onboarding card shows a **🚀 Open in app** tile (plus the
   classic buttons if you picked `hybrid`).
3. Tapping it opens the SPA inside Telegram. You should land on the
   user home (greeting + stats + New-ticket / My-tickets / Settings
   tabs).
4. Open a ticket, send a reply — the message appears in the admin
   topic thread exactly as if it had come from the chat flow.

## 3. Graceful fallback

The bot auto-downgrades to `chat` when any of these apply, so a
misconfigured deploy never emits a broken keyboard:

* `WEBAPP_URL` empty or not `https://`.
* User's Telegram client older than 6.0 (April 2022).
* Transient Mongo error on the per-user preference lookup.

Per-user override: a user can set `ui_pref` from the Mini-App's
**Settings → UI preference** screen. That wins over the global.

## 4. Roll back

```bash
# A) Keep the SPA, turn off WebApp buttons
UI_MODE=chat

# B) Kill the SPA mount entirely (API still up)
WEB_ENABLED=false

# C) Only turn off the menu button (keep hybrid/webapp mode)
WEBAPP_SET_MENU_BUTTON=false
```

Each flip is one redeploy — no DB migrations to reverse, no
collections to clean up.

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/` returns 404 | `WEB_ENABLED=false` or `web/dist` missing | Re-enable the flag; check that `nixpacks` build step completed |
| `/` 200 but JS fails to load | `/assets/*` blocked by CDN | Confirm `/assets/index-*.js` is reachable with 200 |
| `Open App` tap opens a blank screen | Mini-App not registered in BotFather | Redo step 2b |
| `/start` shows no Open-App button | `UI_MODE=chat`, empty `WEBAPP_URL`, or non-https URL | Check env; logs will show `ui_mode=chat` |
| Mini-App shows login screen instead of user home | `initData` invalid — bot token mismatch | Redeploy with the correct `BOT_TOKEN`; initData is signed against that token |
| `401 invalid_init_data:expired` on every call | Device clock far off | Fix client clock; default tolerance is 24h |

## 6. Custom domain

Mini-Apps require a stable HTTPS URL. If you point a custom CNAME at
Railway:

1. Set `WEBAPP_URL=https://support.example.com/` and redeploy.
2. Update the BotFather WebApp domain to the same URL.
3. Railway renews the TLS cert automatically — no action needed.

Changing the domain after launch won't break existing users; the
WebApp just reopens at the new URL on their next tap.
