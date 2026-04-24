# Environment reference

The canonical list lives in
[`.env.example`](https://github.com/davdxpx/XTV-SupportBot/blob/main/.env.example).
This page groups variables by purpose.

## Required

| Variable | Purpose |
|---|---|
| `API_ID` | my.telegram.org API id |
| `API_HASH` | my.telegram.org API hash |
| `BOT_TOKEN` | @BotFather token |
| `MONGO_URI` | MongoDB connection string |
| `ADMIN_IDS` | Comma-separated Telegram user ids |
| `ADMIN_CHANNEL_ID` | Forum supergroup id (`-100…`) |

## Telegram session

| Variable | Default | Notes |
|---|---|---|
| `SESSION_DIR` | `"."` | Directory pyrofork writes `*.session` to. On ephemeral hosts (Railway, Render, Fly, Heroku) point this at a persistent volume (e.g. `/data`) or every deploy re-runs `auth.ImportBotAuthorization` and Telegram rate-limits the bot with `FLOOD_WAIT_X`. |

## Logging

`LOG_LEVEL`, `LOG_JSON`, `DEBUG_MODE`, `ERROR_LOG_TOPIC_ID`.

## SLA / auto-close / cooldown

`SLA_WARN_MINUTES`, `SLA_BREACH_MINUTES`, `AUTO_CLOSE_DAYS`,
`AUTO_CLOSE_SWEEP_MINUTES`, `COOLDOWN_RATE`, `COOLDOWN_WINDOW`,
`COOLDOWN_MUTE_SECONDS`.

## i18n

`DEFAULT_LANG` (default `en`).

## Redis (optional)

`REDIS_URL`, `REDIS_NAMESPACE`.

## AI (optional)

`AI_ENABLED`, `AI_MODEL_DEFAULT`, `AI_MODEL_FAST`, `AI_MODEL_VISION`,
`AI_MODEL_TRANSCRIBE`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`,
`AI_REQUEST_TIMEOUT_S`, `AI_PII_REDACTION`. Provider keys:
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.

## Feature flags

`FEATURE_AI_DRAFTS`, `FEATURE_AI_SUMMARY`, `FEATURE_AI_SENTIMENT`,
`FEATURE_AI_ROUTING`, `FEATURE_AI_TRANSLATE`,
`FEATURE_AI_TRANSCRIBE`, `FEATURE_AI_KB_DRAFTER`,
`FEATURE_BUSINESS_HOURS`, `FEATURE_CSAT`,
`FEATURE_ANALYTICS_DIGEST`, `FEATURE_KB_GATE`,
`FEATURE_LINK_SCANNER`, `FEATURE_START_CAPTCHA`,
`FEATURE_WEBHOOKS_OUT`, `FEATURE_DISCORD_BRIDGE`,
`FEATURE_SLACK_BRIDGE`, `FEATURE_EMAIL_INGRESS`,
`FEATURE_NEW_ONBOARDING`, `FEATURE_CUSTOMER_HISTORY_PIN`,
`FEATURE_AGENT_INBOX`.

## Integrations

`WEBHOOK_SECRET`, `CAPTCHA_SECRET`, `DISCORD_WEBHOOK_URL`,
`SLACK_WEBHOOK_URL`, `DIGEST_TOPIC_ID`.

## REST API

| Variable | Default | Notes |
|---|---|---|
| `API_ENABLED` | `false` | Set `true` to serve the FastAPI app alongside pyrofork |
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Local bind port; `$PORT` (Railway / Render / Fly / Heroku) takes precedence via `settings.effective_api_port` |
| `API_CORS_ORIGINS` | `""` | Comma-separated allow-list; `*` allows everything |
| `API_RATE_LIMIT_PER_MINUTE` | `120` | Per-key token bucket; needs Redis for multi-replica |

Scopes recognised by `/apikey create`: `tickets:read`, `tickets:write`,
`projects:read`, `projects:write`, `users:read`, `analytics:read`,
`webhooks:write`, `rules:read`, `rules:write`, `admin:full`.

See also [API quickstart](api-quickstart.md),
[API authentication](api-auth.md), and the dedicated
[Railway guide](../ops/railway.md).

## Admin SPA

| Variable | Default | Notes |
|---|---|---|
| `WEB_ENABLED` | `true` | Mount the built React SPA at `/` with an `index.html` fallback so React-Router paths survive a refresh |
| `WEB_DIST_DIR` | `web/dist` | Path (from repo root) to the build output; override only if your CI puts it somewhere else |

## Dual-mode UI (Telegram WebApp)

See [Web App feature](../features/web-app.md) and the dedicated
[Deploy the Web App](../ops/deploy-webapp.md) guide for the full story.

| Variable | Default | Notes |
|---|---|---|
| `UI_MODE` | `chat` | `chat` / `webapp` / `hybrid`. Typo-tolerant — unknown values fall back to `chat` |
| `WEBAPP_URL` | `""` | Public HTTPS URL of the Mini-App. Must match the WebApp domain configured via @BotFather |
| `WEBAPP_SET_MENU_BUTTON` | `false` | When true, the bot calls `setChatMenuButton` at boot so every chat shows a persistent "Open App" button |
| `WEBAPP_MENU_BUTTON_TEXT` | `Open App` | Label for the global menu button |

Per-user overrides (`users.ui_pref` + graceful fallback for old
clients or empty `WEBAPP_URL`) are described in the feature doc.

## Observability

`METRICS_ENABLED`, `METRICS_PATH`, `OTEL_SERVICE_NAME`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`,
`OTEL_TRACES_SAMPLER`, `OTEL_TRACES_SAMPLER_ARG`.
