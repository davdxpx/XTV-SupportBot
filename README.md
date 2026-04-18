# XTVfeedback-bot

Telegram support + feedback + direct-contact bot. Every ticket is a **Telegram forum topic** in the admin supergroup, so the entire team can collaborate per user.

## Highlights

- **Forum-topic tickets**: one topic per conversation, with a live header card (assignee, tags, priority, SLA progress bar)
- **Consistent blockquote UI**: every message uses an expandable `<blockquote>` with optional progress bars
- **Assignment**: `Assign` button or `/assign me|<id>|none` in a topic
- **Tags**: admin-managed tag registry, per-ticket multi-toggle picker, `/tag add|rm` in a topic
- **SLA timer**: configurable warning deadline, automatic alert in the topic + header rerender
- **Auto-close**: inactive tickets are closed after `AUTO_CLOSE_DAYS`
- **Anti-spam cooldown**: sliding-window rate limit with mute + strike escalation
- **Broadcast**: pausable/cancellable sender with a live progress card in the admin DM
- **Projects**: support or feedback-type projects; feedback projects auto-close and can collect star ratings
- **Contact links**: one-click deep link that opens a private thread with a specific admin (optionally anonymous)
- Full async stack: **pyrofork + motor**, structlog, pydantic-settings

## Requirements

- Python **3.12**
- A Telegram **forum supergroup** with topics enabled
- The bot must be an admin of the supergroup with the **Manage Topics** permission
- MongoDB (Atlas or self-hosted)
- `API_ID` / `API_HASH` from <https://my.telegram.org>
- Bot token from [@BotFather](https://t.me/BotFather)

## Setup

```bash
# create and activate a Python 3.12 virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# install
pip install -e .

# configure
cp .env.example .env
# edit .env with your values
```

### .env

Required:

- `API_ID`, `API_HASH`, `BOT_TOKEN`
- `MONGO_URI`
- `ADMIN_IDS` (comma-separated Telegram user ids)
- `ADMIN_CHANNEL_ID` (the forum-supergroup id, usually negative and starts with `-100`)

Optional tuning (defaults shown in `.env.example`):

- SLA: `SLA_WARN_MINUTES`, `SLA_BREACH_MINUTES`
- Auto-close: `AUTO_CLOSE_DAYS`, `AUTO_CLOSE_SWEEP_MINUTES`
- Cooldown: `COOLDOWN_RATE`, `COOLDOWN_WINDOW`, `COOLDOWN_MUTE_SECONDS`
- Broadcast: `BROADCAST_CONCURRENCY`, `BROADCAST_FLOOD_BUFFER_MS`
- Progress edits: `PROGRESS_EDIT_INTERVAL`
- Topic creation retries: `TOPIC_CREATE_RETRY`
- Error reporting topic: `ERROR_LOG_TOPIC_ID`
- Audit retention: `AUDIT_RETENTION_DAYS`
- Logging: `LOG_LEVEL`, `LOG_JSON`

### Admin group setup

1. Create a new Telegram group.
2. Promote it to a supergroup and enable **Topics** in group settings.
3. Add the bot as an **administrator** with **Manage Topics** and **Invite Users** permissions.
4. Copy the group's numeric id into `ADMIN_CHANNEL_ID` (supergroup ids usually look like `-1001234567890`).

If topics are not enabled or the bot lacks the permission, the bot falls back to sending ticket messages directly into the channel and marks the ticket with `topic_fallback=true`. Admins can still reply, but without a dedicated thread.

## Run

```bash
python main.py
```

The first boot runs `db.migrations.run()`, which ensures indexes and back-fills missing fields for the new features (assignee, tags, priority, SLA, cooldown, etc.). Migrations are idempotent.

## Commands

### Private chat (users)

- `/start` — select a project or resolve a deep link (`?start=<project_id>` or `?start=contact_<uuid>`)
- `/close` — close the caller's active ticket

### Private chat (admins)

- `/admin` — open the admin dashboard
- `/history <user_id>` — recent tickets for a user

### In a ticket topic (admins)

- Any non-command message is forwarded to the user
- `/close` — close the ticket and its topic
- `/assign <user_id|me|none>` — assign an admin or clear the assignee
- `/tag add|rm <name>` — toggle a tag on the ticket
- Inline buttons on the header card: **Assign**, **Tag**, **Priority**, **Close**

## Testing manually (end-to-end)

1. `/start` in a private chat shows the welcome card.
2. Pick a project, send a text — a new topic appears in the admin group with the ticket header (blockquote + progress bar). The user receives a confirmation card.
3. Reply inside the topic; the user receives the reply as a `Support reply` blockquote.
4. Click `Assign` on the header, pick another admin — the header re-renders and that admin gets a DM.
5. Click `Tag`, toggle two tags — the header shows `#tag1 #tag2`.
6. Send 11 messages in 60 s from the user — message 11 gets a cooldown card; further messages are dropped until the mute elapses.
7. Leave the ticket unanswered past `SLA_WARN_MINUTES` — an SLA alert is posted to the topic and the header bar flips to breached.
8. `/admin ›› Broadcast` — type a text, preview, hit `Start`; the admin DM shows a live progress card with **Pause**/**Resume**/**Cancel**.
9. Leave a ticket inactive for `AUTO_CLOSE_DAYS` — the next auto-close sweep closes it and the user gets an info card.

## Tests

```bash
pip install -e '.[dev]'
pytest
```

## Architecture

```
app/
  core/        filters, router, errors, logger, context, callback_data
  db/          motor client + per-collection repositories, migrations
  services/    ticket / topic / broadcast / cooldown / sla / autoclose / audit
  ui/          Card, ProgressCard, blockquote, progress bar primitives
    templates/ ticket_header, admin_dashboard, project_wizard, broadcast,
               user_messages
  middlewares/ logging, blocked-user drop, cooldown guard, admin_guard
  handlers/    start, user/*, admin/*, topic/*, errors
  tasks/       TaskManager, sla_task, autoclose_task
main.py        asyncio.run(_amain()): client.start -> build_context ->
               register_all -> run loops -> idle -> clean shutdown
```

Message dispatch uses explicit handler groups (`HandlerGroup` in `app/constants.py`) so admin flows, user flows and topic flows never cross.

## Security notes

- The previous version of `.env.example` committed a real bot token and a MongoDB URI with password. **Rotate both** (new token via @BotFather, new MongoDB password in Atlas). The leak remains in git history.
- Secrets in this rewrite are wrapped in `pydantic.SecretStr`.
- Every sensitive admin action (assign, block, broadcast, project delete, tag CRUD) is written to the `audit_log` collection with a TTL of `AUDIT_RETENTION_DAYS` days.

## License / credits

Developed by @davdxpx
