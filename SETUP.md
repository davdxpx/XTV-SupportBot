# XTVfeedback-bot — Setup Guide

Step-by-step to go from zero to a running bot. Follow in order.

---

## 1. Telegram prerequisites

### 1a. Create the bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. `/newbot` → pick a name and a `@username`.
3. Copy the **HTTP API token**. This is your `BOT_TOKEN`.
4. `/setprivacy` → select the bot → **Disable**. The bot needs to read non-reply messages in its admin supergroup.
5. `/mybots` → select the bot → **Bot Settings** → **Allow Groups?** → **Turn on**.

### 1b. Get API_ID and API_HASH

1. Log in to <https://my.telegram.org> with your Telegram account.
2. **API development tools** → create an app (any name, platform "Other").
3. Copy **API ID** (`API_ID`) and **API Hash** (`API_HASH`).

---

## 2. Admin forum supergroup

The bot needs **one** supergroup with Topics (forum) enabled. Every ticket becomes a topic there.

### 2a. Create the group

1. In Telegram: **New Group** → pick a name (e.g. *XAdmin & Support*).
2. Add at least one other member (Telegram requires ≥2 for groups). Can be a second account of yours.
3. Tap the group name → **⋮ / Edit** → **Group Type** → **Public / Private**. Either works.
4. Tap the group name → **⋮ / Edit** → **scroll to bottom** → **Topics** → **toggle on**. Confirm.

This automatically converts the chat into a supergroup and activates the forum view.

### 2b. Add the bot as admin

1. In the supergroup: tap the title → **Add member** → pick your bot (`@YourBot`) → Add.
2. Tap the title → **Administrators** → **Add Admin** → pick the bot.
3. Enable these permissions:
   - ✅ **Manage Topics** (required)
   - ✅ **Send Messages**
   - ✅ **Send Media**
   - ✅ **Pin Messages** (optional, used when re-pinning ticket headers)
   - ✅ **Delete Messages** (optional, for cleanup)
   - ❌ "Anonymous" — **leave off**.

Save.

### 2c. Get the supergroup ID

Supergroup IDs are negative and start with `-100`.

- Easiest: forward any message from the group to [@userinfobot](https://t.me/userinfobot). It replies with `Id: -1001234567890`.
- Alternative: start the bot temporarily, send a dummy message in the group, and read `msg.in chat_id=…` from the logs.

Put that id into `ADMIN_CHANNEL_ID`.

### 2d. Get your own user id (for `ADMIN_IDS`)

Send `/start` to [@userinfobot](https://t.me/userinfobot). It shows your numeric `Id`. Put it into `ADMIN_IDS` (comma-separated if several admins).

---

## 3. MongoDB

The bot uses MongoDB to store tickets, projects, users, tags, broadcasts and audit logs.

### Option A — MongoDB Atlas (hosted, recommended)

1. Sign up at <https://www.mongodb.com/atlas>, create a free cluster.
2. **Database Access** → **Add New User** → username + password.
3. **Network Access** → **Add IP Address** → `0.0.0.0/0` (or Railway's outbound IPs).
4. **Connect** → **Drivers** → **Python** → copy the `mongodb+srv://…` URI. Replace `<password>` with the actual password.
5. Put the full URI into `MONGO_URI`.

### Option B — self-hosted

Run MongoDB 5.0+ locally or on a VPS. `MONGO_URI=mongodb://user:pass@host:27017/xtvfeedback_bot`.

---

## 4. Configure `.env`

Copy `.env.example` to `.env` and fill in the required values:

```env
API_ID=12345
API_HASH=0123456789abcdef
BOT_TOKEN=1234567890:ABC-DEF...

MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/xtvfeedback_bot

ADMIN_IDS=111111111,222222222
ADMIN_CHANNEL_ID=-1001234567890
```

The remaining values (SLA, cooldown, broadcast, log level, ...) have sensible defaults — override only if needed. See `.env.example` for every option.

---

## 5. Run

### Local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Docker

```bash
docker build -t xtvfeedback-bot .
docker run --rm --env-file .env xtvfeedback-bot
```

### Railway

1. Create a new Railway project linked to your GitHub fork/branch.
2. Add all the env vars from `.env` under **Variables**.
3. Railway auto-detects `requirements.txt` + `Procfile` / `nixpacks.toml` and runs `python main.py`.

### VPS (systemd)

Create `/etc/systemd/system/xtvfeedback-bot.service`:

```ini
[Unit]
Description=XTVfeedback-bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/srv/xtvfeedback-bot
EnvironmentFile=/srv/xtvfeedback-bot/.env
ExecStart=/srv/xtvfeedback-bot/.venv/bin/python main.py
Restart=always
RestartSec=5
User=bot

[Install]
WantedBy=multi-user.target
```

`systemctl daemon-reload && systemctl enable --now xtvfeedback-bot`.

---

## 6. First run checklist

The bot prints a detailed boot log. Everything in green should match:

```
boot.bot_identity id=… username=@YourBot name=… is_bot=True
boot.admin_chat  id=-100… title='…' type=ChatType.FORUM is_forum=True members=3
mongo.connected  db=xtvfeedback_bot
db.indexes_ensured
router.registered modules=18 handlers=63
scheduler.spawned name=sla_loop
scheduler.spawned name=autoclose_loop
boot.ready
```

If you see **`boot.admin_chat_not_forum`** or **`boot.admin_chat_unreachable`**, the forum step was not completed or the bot is not in the group yet. Go back to step 2.

---

## 7. Smoke test

1. **User side.** Open a DM to your bot and send `/start`.
   Expected: Welcome card with a list of projects (empty at first).
2. **Admin side.** Send `/admin` to the bot in DM.
   Expected: Admin dashboard (projects, users, tickets counters + module buttons).
3. In the dashboard: **Manage Projects → Create new project**. Walk through name → description → type = Support. A confirmation card appears.
4. Back to the user DM. `/start` again. Pick the new project. Send a text.
   Expected:
   - a new forum topic appears in the admin supergroup, title `#<id> • <project>`
   - the topic contains the ticket header card (user info, SLA, buttons) and your original message
   - your DM receives `🎫 Ticket #<id> created`
5. In the topic (admin side), reply to the ticket.
   Expected: The user receives your reply in DM as `💬 Support reply`.
6. `/close` in the topic closes it and notifies the user.

If step 4 fails, check the next section.

---

## 8. Troubleshooting

### `CreateForumTopic ... channel` / `TypeError`
Update pyrofork (`pip install -U pyrofork`). The bot already falls back to the raw-API path in `app/services/topic_service.py`; this error means **both** paths failed. Usually a missing **Manage Topics** permission — revisit step 2b.

### `DuplicateKeyError: ux_topic_id dup key: { topic_id: null }`
Only happens on databases created before schema v3. The bot runs the migration automatically on the next boot (it drops the old index and recreates it with a partial filter). If it still appears: manually drop the index in Atlas (`db.tickets.dropIndex("ux_topic_id")`) and restart.

### `/start` replies but buttons do nothing
The bot is probably running multiple instances against the same bot token. Only one process at a time — stop the old one.

### User messages land in the admin chat without a thread
That means `topic_fallback=true` was set. Look at the previous boot log for `topic.create_failed` — the root cause is usually a missing permission or disabled Topics in the group.

### `boot.admin_chat_not_forum`
Topics are not enabled in the supergroup. Go to group settings → Topics → toggle on. The bot needs to be re-added after if you accidentally removed it during the conversion.

### Nothing happens when I send messages
Check the logs for `msg.in`. If the message arrives but nothing fires:
- verify `ADMIN_IDS` contains your user id if you're testing `/admin`.
- verify `ADMIN_CHANNEL_ID` matches your supergroup's numeric id.
- verify the bot's **Privacy Mode** is OFF (BotFather → `/setprivacy`).

---

## 9. Security reminders

- Rotate the Bot Token and MongoDB password that were leaked in the original `.env.example`. They are in the public git history.
- `ADMIN_IDS` is a hard allow-list. Treat it like a root password.
- `ERROR_LOG_TOPIC_ID` (optional): if set, internal tracebacks go there — pick a topic that only admins can read.

---

Developed by @davdxpx
