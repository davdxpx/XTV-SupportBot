# Architecture overview

```
src/xtv_support/
  config/          settings, feature flags, i18n loader
  core/            DI container, event bus, router, i18n, rbac, FSM
  domain/          frozen models + events (no IO)
  infrastructure/  db, cache, storage, telegram, ai, metrics, tracing
  services/        bounded-context business logic
  handlers/        pyrofork user/admin/topic/agent handlers
  middlewares/     logging, rbac, i18n, blocked, cooldown, tracing
  ui/              card/blockquote/progress primitives + templates
  plugins/         loader + registry + builtin/* (12 builtins)
  tasks/           scheduler + periodic jobs
  api/             FastAPI REST app (optional)
  utils/           text, time, ids, retry, crypto
  locales/         en + 10 language YAMLs
```

## Lifecycle

1. `main.py` -> `xtv_support.entrypoint()`.
2. Bootstrap builds: pyrofork Client, Container, EventBus,
   FeatureFlags, StateMachine, I18n, AIClient, PluginLoader.
3. Plugins are discovered, gated on their `feature_flag`, started.
4. The router attaches every `@Client.on_message` / `on_callback_query`
   handler defined in `xtv_support.handlers.*` to the live pyrofork Client.
5. Background tasks (SLA sweeper, auto-close, analytics rollup,
   webhook retry, weekly digest) run via the Phase-3 TaskManager.
6. On shutdown the loader unloads plugins, resets i18n, closes Mongo.

See [Plugins](plugins.md) + [Events](events.md) for the details.
