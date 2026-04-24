# Railway deployment guide

End-to-end: from a fresh Railway account to `xtvsupport.up.railway.app`
serving the API and the bot.

## 0. Pre-flight

You need:

- A Telegram bot from [@BotFather](https://t.me/BotFather)
- `API_ID` + `API_HASH` from [my.telegram.org](https://my.telegram.org)
- A Telegram forum supergroup where the bot is an admin with
  **Manage Topics**
- Your Telegram user ID
- A Railway account

## 1. Fork + connect

1. Fork `davdxpx/XTV-SupportBot` on GitHub.
2. On [railway.app](https://railway.app), **New Project → Deploy from
   GitHub repo → pick your fork**.
3. Railway auto-detects `requirements.txt`, `Procfile`, and
   `nixpacks.toml` — no build command to configure manually.

## 2. Add a MongoDB plugin

Railway → your project → **+ Create → Database → MongoDB**. Copy its
connection URI from the plugin's Variables tab.

Alternatively use MongoDB Atlas: create a free-tier cluster, take the
SRV URI.

## 3. Set environment variables

On the service settings → Variables tab, set:

```env
# --- Telegram (required) ---
API_ID=123456
API_HASH=abcdef123…
BOT_TOKEN=1234567890:AAA…

# --- MongoDB (required) ---
MONGO_URI=mongodb+srv://…
MONGO_DB_NAME=xtv_support

# --- Roles (required) ---
ADMIN_IDS=123456789,987654321
ADMIN_CHANNEL_ID=-1001234567890

# --- REST API ---
API_ENABLED=true
API_CORS_ORIGINS=*                # tighten once the admin SPA is up

# Optional:
LOG_LEVEL=INFO
DEFAULT_LANG=en
```

Notes:

- `PORT` is injected by Railway automatically — you don't set it.
  `settings.effective_api_port` picks it up.
- `API_CORS_ORIGINS=*` is fine for the quickstart; use a real origin
  (`https://admin.yourco.com`) once you have one.

## 4. Deploy

Railway redeploys automatically on every push to the connected branch.
Watch the **Deployments** tab for the build + run logs.

The boot sequence you should see:

```
boot.environment python=3.12 …
boot.settings …
boot.client_starting
boot.bot_identity id=… username=@YourBot
boot.admin_chat id=-100… is_forum=True
boot.api_started host=0.0.0.0 port=12345 …
boot.ready admins=2 …
```

If `boot.admin_chat_unreachable` appears: the bot isn't a member of
the forum supergroup, or lacks **Manage Topics**. Fix in Telegram, no
redeploy needed — next run will pick it up.

## 5. Verify the public URL

Railway assigns a domain like `<service>.up.railway.app`. Find it in
the **Networking → Public URL** section.

```bash
export BASE=https://xtvsupport.up.railway.app   # your actual URL
curl -sS $BASE/health | jq .
curl -sS $BASE/ready  | jq .
curl -sS $BASE/api/v1/version | jq .
```

Expected: `{"ok": true, "version": "0.9.0"}` and friends.

Open `$BASE/api/v1/docs` in a browser for Swagger UI.

## 6. Create an API key

Follow the [API quickstart](../reference/api-quickstart.md#2-mint-an-api-key).

## 7. Custom domain

Railway → service → **Networking → Custom Domains**, add yours, update
the DNS `CNAME`. The public Railway URL keeps working alongside the
custom domain.

## 8. Logs

Railway streams logs in the **Observability** tab and from the CLI:

```bash
npx @railway/cli logs --follow
```

`LOG_JSON=true` in env flips structured logging on — pipe the output
into anything that speaks JSON (Datadog, Loki, Grafana Cloud).

## 9. Scaling caveat

`replicaCount=1` is the only supported shape today: pyrofork holds a
single session file, and a second instance would fight for it. Railway
defaults to 1 replica — leave it that way until multi-session brokering
ships in a later release.

The `web:` process the `Procfile` declares is the bot + API on the
same asyncio loop in one process. Don't add a `worker:` process.

## 10. Rollback

Railway → **Deployments** → pick the previous successful one → **Redeploy**.
Every phase commit in the current v0.9 pre-release is reverse-compatible
at the DB level (migrations are idempotent `$set` + `$setOnInsert`),
so rollbacks are safe.

## 11. Railway CLI cheat-sheet

```bash
# Install
npm i -g @railway/cli
railway login

# Link to a project
railway link

# Local dev against the prod Mongo
railway run python main.py

# Tail logs
railway logs --service xtv-support

# Bump an env var
railway variables set API_CORS_ORIGINS=https://admin.example.com
```

## 12. Production hardening checklist

Before you send users to the bot:

- [ ] `API_ENABLED=true` and `$BASE/health` returns `200`
- [ ] `ADMIN_IDS` matches the actual admin list
- [ ] The bot is **admin with Manage Topics** in the forum supergroup
- [ ] `WEBHOOK_SECRET` set if `FEATURE_WEBHOOKS_OUT=true`
- [ ] `API_CORS_ORIGINS` tightened to real origins
- [ ] MongoDB backups configured (Atlas does them automatically; the
      Railway Mongo plugin needs a scheduled dump)
- [ ] `LOG_JSON=true` + log drain wired
- [ ] At least one **narrow-scope** API key in use (not `admin:full`)
  for production integrations
- [ ] First end-to-end test: `/start` in DM, open a ticket, close it
      from the topic

## Troubleshooting

See the [API quickstart troubleshooting table](../reference/api-quickstart.md#7-troubleshooting)
for API-side issues. For bot-side issues, the `boot.*` log lines
usually point straight at the misconfiguration.
