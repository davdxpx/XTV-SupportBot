# XTV-SupportBot

<p align="center">
  <b>Enterprise-grade Telegram support, feedback and direct-contact bot.</b><br>
  Forum-topic tickets · RBAC &amp; teams · macros &amp; knowledge base · AI assistance ·
  analytics · broadcasts · plugins · REST API &amp; web admin.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.9.0-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&amp;logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-XTV%20Public%20License-lightgrey">
  <img alt="Status" src="https://img.shields.io/badge/status-pre--release-orange">
</p>

> **v0.9.0 is a public pre-release** on the way to a stable v1.0. Interfaces may
> still change between minor versions. Bug reports and PRs are welcome — see
> `CONTRIBUTING.md`.

---

## What it does

XTV-SupportBot turns a single Telegram forum supergroup into a full-featured
helpdesk. Every conversation with an end-user is a **forum topic**; the whole
team can collaborate inside it with live-updated header cards, assignment,
tags, priority, SLA timers and canned replies.

## Feature matrix

| Area | Features |
|---|---|
| **Tickets** | forum-topic per ticket, live header card, assignment, tags, priority, SLA + breach alerts, auto-close |
| **Teams &amp; roles** | RBAC (`owner`/`admin`/`supervisor`/`agent`/`viewer`), queue routing by tag/project/priority |
| **Productivity** | macros / canned responses, knowledge base with FTS &amp; pre-ticket FAQ gate, inline autocompletion |
| **AI** (opt-in) | reply drafts, ticket summaries, sentiment, smart routing, translation, voice/image OCR — via **LiteLLM** (Claude, GPT, Gemini, Ollama, …) |
| **Escalation &amp; CSAT** | escalation rules, business hours &amp; holidays, 1–5★ CSAT after close |
| **Analytics** | FRT/resolution/SLA metrics, agent leaderboard, weekly digest, CSV/JSON exports |
| **Integrations** | outgoing HMAC-signed webhooks, Discord/Slack bridge, optional email ingestion |
| **Anti-spam** | sliding-window cooldown + mute, CAPTCHA plugin, link/phishing scanner |
| **Broadcast** | pausable/cancellable with live progress card |
| **Compliance** | GDPR export/delete, audit log with TTL, PII-redaction filter |
| **API &amp; web** | FastAPI REST (API-keys &amp; scopes), React/Vite SPA admin under `/web/` |
| **Observability** | Prometheus `/metrics`, OpenTelemetry traces, `/health` &amp; `/ready` |
| **i18n** | English + Spanish, Russian, Hindi, Bengali, Tamil, Telugu, Marathi, Punjabi, Gujarati, Urdu |
| **Ops** | multi-stage Docker image, docker-compose, Helm chart, raw k8s manifests, Railway/Nixpacks |

## Tech stack

- Python **3.12**, async everywhere
- `pyrofork` (Telegram MTProto) + `tgcrypto`
- `motor` (MongoDB async) — primary datastore
- Optional `redis` for distributed cache / cooldown / rate-limits
- `pydantic-settings`, `structlog`
- `LiteLLM` for provider-agnostic AI
- `FastAPI` for the REST/admin API, React + Vite for the SPA
- `Prometheus` + `OpenTelemetry` for observability

## Install

### pip extras

```bash
pip install -e '.[dev]'            # minimum
pip install -e '.[ai,api,redis]'   # enable AI, REST API, Redis cache
pip install -e '.[all]'            # everything including docs & observability
```

### Docker (single image, SPA baked in)

```bash
docker build -f deploy/docker/Dockerfile -t xtv-support:0.9.0 .
docker run --rm --env-file .env xtv-support:0.9.0
```

### docker-compose (bot + mongo + redis + prometheus)

```bash
docker compose -f deploy/compose/docker-compose.yml up
```

### Helm (Kubernetes)

```bash
helm install xtv-support deploy/helm/xtv-support \
  --set-file env.env=./.env \
  --set image.tag=0.9.0
```

### Railway / Nixpacks / VPS

`Procfile` &amp; `nixpacks.toml` remain unchanged — `python main.py` is the entry
point. See `SETUP.md` for the end-to-end walkthrough.

## Quick start (local)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

cp .env.example .env           # fill in API_ID/API_HASH/BOT_TOKEN/MONGO_URI/ADMIN_IDS/ADMIN_CHANNEL_ID

python main.py
```

See **`SETUP.md`** for the fully-annotated walkthrough (BotFather, forum
supergroup, MongoDB Atlas, Railway/Docker, smoke-test checklist).

## Configuration

Every setting is read from environment variables or `.env`. See
`.env.example` for the complete, commented list. Feature modules that are
shipped as opt-in plugins are **off by default** — flip them on by setting
their `FEATURE_*` flag to `true`.

## Commands (excerpt)

### User DM
- `/start` · `/close` · `/lang` · `/tickets` · `/gdpr export|delete`

### Admin DM
- `/admin` (dashboard) · `/history <user_id>` · `/team create` · `/apikey create <scope>`

### Inside a ticket topic
- Any non-command text → forwarded to user
- `/close` · `/assign <user_id|me|none>` · `/tag add|rm <name>`
- `/macro save|use|list` · header buttons: *Assign*, *Tag*, *Priority*, *AI Draft*, *Close*

## Architecture

```
src/xtv_support/
  config/          settings, feature flags, i18n config
  core/            DI container, event bus, router, filters, logger, FSM
  domain/          pure models &amp; events
  infrastructure/  db, cache, storage, telegram, ai (LiteLLM), metrics, tracing
  services/        tickets, projects, users, sla, cooldown, broadcasts, macros,
                   kb, ai, analytics, escalation, csat, teams, business_hours, gdpr
  handlers/        user/ admin/ topic/ system/
  middlewares/     logging, admin_guard, blocked, cooldown, i18n, rbac, rate_limit, tracing
  ui/              primitives (card/progress/blockquote), templates, themes, keyboards
  plugins/         loader + registry + builtin/*
  tasks/           scheduler + periodic jobs
  api/             FastAPI app (routes, deps, security)
  utils/           text, time, ids, retry, crypto, phone, validation
  locales/         en.yaml, ru.yaml, …
```

The full layered diagram lives in `docs/architecture.md`.

## Documentation

- **`SETUP.md`** — step-by-step first-run guide
- **`docs/`** (MkDocs-Material) — full reference, plugin authoring, API, deployment
- **`CHANGELOG.md`** · **`SECURITY.md`** · **`CONTRIBUTING.md`** · **`CODE_OF_CONDUCT.md`**

## Security

- Every admin action is written to an audit log with configurable TTL
- Inbound link/phishing scanner is on by default; abusers are auto-muted
- API keys are SHA-256-hashed at rest; full key is shown exactly once
- Webhook deliveries are HMAC-SHA-256 signed
- Secret-rotation helper: `python scripts/rotate_secrets.py`

Report vulnerabilities privately — see `SECURITY.md`.

## License

Source-available under the **XTV Public License** — see `LICENSE`. For
licensing inquiries reach out on Telegram [@davdxpx](https://t.me/davdxpx).

## Credits

Developed by **𝕏0L0™** ([@davdxpx](https://t.me/davdxpx)) for the
[𝕏TV Network](https://t.me/XTVglobal) · bots channel:
[@XTVbots](https://t.me/XTVbots) · backup: [@XTVhome](https://t.me/XTVhome).

Developed by @davdxpx
