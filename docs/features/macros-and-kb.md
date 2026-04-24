# Macros + Knowledge Base

## Macros

Canned replies scoped to a team or global. Inside a ticket topic:

```
/macro list
/macro save <name>          # body = replied-to message
/macro save <name> <body>   # inline
/macro use <name>
/macro show <name>
/macro del <name>
```

Macros support `{user_name}` / `{user_id}` / `{ticket_id}`
placeholders. Every use bumps `usage_count` and publishes a
`MacroUsed` event.

## Knowledge Base

Admin-curated articles with full-text search backed by MongoDB's
text index (title weight 10, body 3, tags 5).

```
/kb list [lang]
/kb show <slug>
/kb add <slug> | <title> | <body>
/kb edit <slug> body: <text>   # or title: / tags: / lang:
/kb del <slug>
/kb search <query>
```

## Pre-ticket KB gate

With `FEATURE_KB_GATE=true`, a user's first message in a ticket
conversation is matched against the KB. Up to 3 articles appear as
inline buttons with an escape hatch:

- Click an article → view the body, click ✅ or 🙋 *I still need help*.
- `/humanplease` — bypass the gate for the next message.
