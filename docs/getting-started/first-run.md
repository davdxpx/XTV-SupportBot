# First run

1. Start the bot: `python main.py` (or `docker run …`).
2. In your admin DM: `/start` should greet you.
3. `/admin` opens the dashboard.
4. **Manage Projects → Create**. Pick a name + type (support / feedback).
5. From a second Telegram account, open the bot, send `/start`, select
   the project, send a message. A forum topic appears in your admin
   supergroup.

## Smoke checks

The boot log should contain:

```
boot.bot_identity       id=… username=@YourBot
boot.admin_chat         type=ChatType.FORUM  is_forum=True
mongo.connected
db.indexes_ensured
i18n.loaded             supported=[en, ru, es, hi, …]
ai.configured           enabled=false
plugins.loaded          total=N loaded=1 failed=0 disabled=N-1
router.registered       modules=… handlers=…
boot.ready
```

If `boot.admin_chat_not_forum` shows, enable Topics in the supergroup
and re-check the bot's admin permissions (Manage Topics is required).
