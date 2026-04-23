# Deployment

See [Install](../getting-started/install.md) for the four supported
paths (pip / Docker / compose / Helm). This page covers ops concerns
specific to each.

## Single-holder pyrofork session

The pyrofork session file can be held by exactly one process at a
time. That's why:

- The Helm chart uses `strategy: Recreate` instead of `RollingUpdate`.
- `replicaCount=1` is the only safe default. Scaling requires
  external session brokering (planned for a later phase).

## Sessions & persistence

- Mongo is the durable store. Back up `tickets`, `users`, `projects`,
  `teams`, `roles`, `macros`, `kb_articles`, `analytics_daily`.
- The session file (`*.session`) is created next to `main.py` at
  first boot. Mount a volume in Docker / Helm to preserve it across
  restarts and avoid Telegram re-logins.

## Updating

1. Bump `image.tag`.
2. `helm upgrade xtv-support …` or redeploy compose.
3. Migrations are idempotent — Phase 3/5/6/9 bumps all carry safe
   `update_many` backfills. First boot after a major version should
   show the new `SCHEMA_VERSION` in `db.backfill_defaults_done`.
