<div align="center">

# 𝕏TV-SupportBot

> *Developed by [𝕏0L0™](https://t.me/davdxpx) for the [𝕏TV Network](https://t.me/XTVglobal)*

<p align="center">
  <img src="./assets/banner.png" alt="𝕏TV SupportBot™ Banner" width="100%">
</p>

**An enterprise-grade Telegram support, feedback and contact bot.**
*Forum-topic tickets · RBAC & teams · macros & knowledge base · AI assistance ·
analytics · broadcasts · plugins · REST API & web admin.*

[![Version](https://img.shields.io/badge/version-0.9.0-blue)](https://github.com/davdxpx/XTV-SupportBot/releases)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![License](https://img.shields.io/badge/license-%F0%9D%95%8FTV%20Public%20License-lightgrey)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--release-orange)](CHANGELOG.md)
[![Docs](https://img.shields.io/badge/docs-MkDocs%20Material-526cfe?logo=materialformkdocs&logoColor=white)](https://davdxpx.github.io/XTV-SupportBot/)
[![Telegram](https://img.shields.io/badge/Telegram-%40XTVbots-229ED9?logo=telegram&logoColor=white)](https://t.me/XTVbots)

[**Documentation**](https://davdxpx.github.io/XTV-SupportBot/) ·
[Setup](SETUP.md) ·
[Changelog](CHANGELOG.md) ·
[Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md) ·
[Telegram](https://t.me/davdxpx)

</div>

---

> **v0.9.0 is a public pre-release** on the way to a stable v1.0.
> Interfaces may still change between minor versions. Bug reports and pull
> requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Table of contents

- [Why XTV-SupportBot](#why-xtv-supportbot)
- [Quick start](#quick-start)
- [Feature matrix](#feature-matrix)
- [Tech stack](#tech-stack)
- [Install](#install)
- [Configuration](#configuration)
- [Commands](#commands)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Security](#security)
- [Contributing](#contributing)
- [Community & support](#community--support)
- [License & credits](#license--credits)

## Why XTV-SupportBot

XTV-SupportBot turns a single Telegram forum supergroup into a **full helpdesk**:

- **Every user conversation is a forum topic** in your admin group. The whole
  team collaborates inside it with a live-updating header card, assignment,
  tags, priority, SLA timers and canned replies.
- **RBAC + teams + routing.** Owner / admin / supervisor / agent / viewer
  roles; declarative queue routing by tag, project, priority.
- **Productivity out of the box.** Macros with placeholders, a searchable
  knowledge base, pre-ticket FAQ gate that deflects common questions before
  a ticket is even opened.
- **AI when you need it.** Reply drafts, summaries, sentiment, smart routing,
  translation, voice/image OCR — all opt-in, provider-agnostic via
  [LiteLLM](https://docs.litellm.ai/) (Claude, GPT, Gemini, local Ollama…).
- **Ops-friendly from day one.** Prometheus `/metrics`, OpenTelemetry traces,
  `/health` + `/ready` probes, HMAC-signed outbound webhooks, GDPR
  export/delete, audit log with TTL.
- **Deploy however you want.** Single Python process; ships with a multi-stage
  Docker image, `docker-compose`, Helm chart, raw k8s manifests and a
  Railway/Nixpacks config.

Full feature tour: **[davdxpx.github.io/XTV-SupportBot](https://davdxpx.github.io/XTV-SupportBot/)**.

## Quick start

```bash
# 1. Clone and set up the environment
git clone https://github.com/davdxpx/XTV-SupportBot.git
cd XTV-SupportBot
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# 2. Configure
cp .env.example .env
# fill in API_ID, API_HASH, BOT_TOKEN, MONGO_URI,
#         ADMIN_IDS, ADMIN_CHANNEL_ID
#   — see the Getting-Started guide for how to obtain each value:
#     https://davdxpx.github.io/XTV-SupportBot/getting-started/install/

# 3. Run
python main.py
```

On first boot you should see `boot.ready` in the log. Send `/start` to your
bot in a private chat to test the user flow.

> Need the end-to-end walkthrough (BotFather, forum supergroup, MongoDB Atlas,
> Railway/Docker, smoke-test checklist)? Follow **[SETUP.md](SETUP.md)** — the
> step-by-step guide from zero to a running bot.

## Feature matrix

| Area | Highlights | Deep-dive |
|---|---|---|
| **Tickets** | forum-topic per ticket, live header card, assignment, tags, priority, SLA + breach alerts, auto-close | [Architecture overview](https://davdxpx.github.io/XTV-SupportBot/architecture/overview/) |
| **Teams & RBAC** | owner / admin / supervisor / agent / viewer; declarative queue routing | [RBAC & teams](https://davdxpx.github.io/XTV-SupportBot/features/rbac-and-teams/) |
| **Macros & KB** | parameterised macros, knowledge base with full-text search, pre-ticket FAQ gate | [Macros & KB](https://davdxpx.github.io/XTV-SupportBot/features/macros-and-kb/) |
| **AI assistance** | reply drafts, summaries, sentiment, smart routing, translation, voice/image OCR (opt-in, via LiteLLM) | [AI features](https://davdxpx.github.io/XTV-SupportBot/features/ai/) |
| **Escalation & CSAT** | escalation rules, business hours & holidays, 1–5★ CSAT after close | [Features index](https://davdxpx.github.io/XTV-SupportBot/#feature-tour) |
| **Analytics** | FRT / resolution / SLA metrics, agent leaderboard, weekly digest, CSV/JSON exports | [Analytics](https://davdxpx.github.io/XTV-SupportBot/features/analytics/) |
| **Integrations** | outgoing HMAC-signed webhooks, Discord / Slack bridges, email ingestion scaffolding | [Integrations](https://davdxpx.github.io/XTV-SupportBot/features/integrations/) |
| **Anti-spam** | sliding-window cooldown + mute, CAPTCHA plugin, link/phishing scanner | — |
| **Broadcast** | pausable / cancellable with a live progress card | — |
| **Compliance** | GDPR export / delete, audit log with TTL, PII-redaction filter | [GDPR](https://davdxpx.github.io/XTV-SupportBot/ops/gdpr/) |
| **REST API & Web** | FastAPI REST (API-keys + scopes), React + Vite admin SPA | [API reference](https://davdxpx.github.io/XTV-SupportBot/reference/api/) |
| **Observability** | Prometheus `/metrics`, OpenTelemetry traces, `/health` + `/ready` | [Observability](https://davdxpx.github.io/XTV-SupportBot/ops/observability/) |
| **i18n** | English + 10 languages (Russian, Spanish, Hindi, Bengali, Tamil, Telugu, Marathi, Punjabi, Gujarati, Urdu) | — |
| **Ops & deploy** | multi-stage Docker, docker-compose, Helm chart, raw k8s manifests, Railway / Nixpacks | [Deployment](https://davdxpx.github.io/XTV-SupportBot/ops/deployment/) |
| **Plugins** | declarative plugin loader; 13 built-in plugins; register custom templates, actions, bridges | [Plugin authoring](https://davdxpx.github.io/XTV-SupportBot/architecture/plugins/) |

## Tech stack

- **Python 3.12**, async everywhere
- [`pyrofork`](https://github.com/Mayuri-Chan/pyrofork) (Telegram MTProto) + [`tgcrypto`](https://github.com/pyrogram/tgcrypto)
- [`motor`](https://motor.readthedocs.io/) (MongoDB async) — primary datastore
- Optional [`redis`](https://redis.io/) for distributed cache / cooldown / rate-limits
- [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [`structlog`](https://www.structlog.org/)
- [`LiteLLM`](https://docs.litellm.ai/) for provider-agnostic AI
- [`FastAPI`](https://fastapi.tiangolo.com/) for the REST API, React + Vite for the admin SPA
- [`Prometheus`](https://prometheus.io/) + [`OpenTelemetry`](https://opentelemetry.io/) for observability

## Install

Pick the flavour that matches your deployment target:

<details open>
<summary><b>pip (local development)</b></summary>

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'            # minimal dev setup (lint/format/tests)
pip install -e '.[ai,api,redis]'   # enable AI, REST API, Redis cache
pip install -e '.[all]'            # everything incl. docs & observability
```

</details>

<details>
<summary><b>Docker (single image, SPA baked in)</b></summary>

```bash
docker build -f deploy/docker/Dockerfile -t xtv-support:0.9.0 .
docker run --rm --env-file .env xtv-support:0.9.0
```

</details>

<details>
<summary><b>docker-compose (bot + Mongo + Redis + Prometheus)</b></summary>

```bash
docker compose -f deploy/compose/docker-compose.yml up
```

</details>

<details>
<summary><b>Helm (Kubernetes)</b></summary>

```bash
kubectl create secret generic xtv-support-secrets --from-env-file=.env
helm install xtv-support deploy/helm/xtv-support --set image.tag=0.9.0
```

</details>

<details>
<summary><b>Railway / Nixpacks / VPS</b></summary>

Repo root ships a thin `Dockerfile`, a `Procfile` and a `nixpacks.toml`.
Push to Railway (or any Nixpacks-aware host), set the env vars from
`.env.example`, and the platform will build + run `python main.py` for you.
See the [Install guide](https://davdxpx.github.io/XTV-SupportBot/getting-started/install/)
for the full walkthrough.

</details>

### Optional extras

```bash
pip install -e '.[redis]'           # Redis cache + distributed cooldown
pip install -e '.[ai]'              # LiteLLM-powered AI features
pip install -e '.[api]'             # FastAPI REST + admin SPA
pip install -e '.[observability]'   # Prometheus + OpenTelemetry
pip install -e '.[all]'             # everything above + docs extras
```

## Configuration

Every setting is read from environment variables or a local `.env`. The
canonical, fully-commented list lives in
[`.env.example`](.env.example). Optional feature modules are **off by
default** — flip them on by setting the matching `FEATURE_*` flag to
`true`.

| Group | Purpose |
|---|---|
| **Required** | `API_ID`, `API_HASH`, `BOT_TOKEN`, `MONGO_URI`, `ADMIN_IDS`, `ADMIN_CHANNEL_ID` |
| **SLA / auto-close** | `SLA_WARN_MINUTES`, `SLA_BREACH_MINUTES`, `AUTO_CLOSE_DAYS`, `AUTO_CLOSE_SWEEP_MINUTES` |
| **Anti-spam** | `COOLDOWN_RATE`, `COOLDOWN_WINDOW`, `COOLDOWN_MUTE_SECONDS` |
| **Feature flags** | `FEATURE_AI_DRAFTS`, `FEATURE_CSAT`, `FEATURE_KB_GATE`, `FEATURE_WEBHOOKS_OUT`, … |
| **Observability** | `METRICS_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, … |

See the full reference: **[Environment variables](https://davdxpx.github.io/XTV-SupportBot/reference/env/)**.

## Commands

The bot is **menu-first**: `/start` for users and `/admin` for admins
open everything as button-driven cards. The commands below are the
**power-user shortcuts** — useful for scripting / automation / keyboard
workflow, but you never *have* to type them.

### User DM

| Command | What it does |
|---|---|
| `/start` | Onboarding panel with New ticket / Browse help / My tickets / Settings. Deep-link payloads open contact or project flows directly. |
| `/home` | Alias for `/start`. |
| `/tickets` | Paginated list of your tickets with unread-reply badges. |
| `/faq` | Pure knowledge-base browse. |
| `/settings` | Language + notification preferences. |
| `/close` | Close your currently-open ticket. |
| `/lang` | Change UI language. |
| `/gdpr_export` | Sends your full data export as a JSON document. |
| `/gdpr_delete` | Two-step deletion with a 30-day grace window. |
| `/humanplease` | Escape the KB gate if it loops. |

### Admin DM

| Command | What it does |
|---|---|
| `/admin` | Tabbed control panel: Overview / Tickets / Teams / Projects / Rules / Broadcasts / Analytics / Settings. (Alias: `/panel`) |
| `/history <user_id>` | Last 10 tickets for a given user. |
| `/apikey [create <scopes> [label] \| revoke <id> \| list]` | API-key lifecycle (gated on `API_ENABLED=true`). |
| `/templates` | List available project templates. |
| `/project_template <template_slug> <project_slug> [name…]` | Create a project from a built-in template. |
| `/team [list \| create \| rename \| delete \| tz \| members \| addmember \| removemember]` | Team CRUD (menu lives under `/admin → Teams`). |
| `/role [list \| grant \| revoke]` | RBAC assignments. |
| `/kb [list \| show \| add \| edit \| del \| search]` | Knowledge-base CRUD. |
| `/rules` + `/rule_new`, `/rule_enable`, `/rule_disable`, `/rule_delete`, `/rule_test` | Automation rules. |

Projects CRUD, broadcasts, and user block/unblock run **only through
the `/admin` dashboard's buttons** — no direct commands for those.

### Agent DM

| Command | What it does |
|---|---|
| `/queue` | Open tickets routed to any team you belong to. |
| `/mytickets` | Tickets currently assigned to you. |
| `/inbox` | Agent cockpit with saved views + bulk actions (gated on `FEATURE_AGENT_INBOX=true`). |

### Inside a ticket topic

| Command / button | What it does |
|---|---|
| *any non-command text* | Forwarded to the user as an admin reply. |
| `/close` | Close the ticket, notify the user, optional CSAT prompt. |
| `/assign <user_id \| me \| none>` | Assign / unassign an agent. |
| `/tag add\|rm <name>` | Mutate ticket tags in-place. |
| `/macro [save \| use \| list \| show \| del]` | Macro library (global + team-scoped). |
| `/note <text>` | Internal note, hidden from the user. |
| `/draft` | Generate an AI reply draft (gated on `FEATURE_AI_DRAFTS`). |
| Header buttons | *Assign*, *Tag*, *Priority*, *AI Draft*, *Close*. |

`/cancel` in any wizard step aborts it and clears the FSM.

The complete, verified-against-code command reference lives in the
docs: **[Command reference](https://davdxpx.github.io/XTV-SupportBot/reference/commands/)**.

## Architecture

```
src/xtv_support/
├─ config/          settings, feature flags, i18n config
├─ core/            DI container, event bus, router, filters, logger, FSM
├─ domain/          pure models & events
├─ infrastructure/  db, cache, storage, telegram, ai (LiteLLM), metrics, tracing
├─ services/        tickets, projects, users, sla, cooldown, broadcasts, macros,
│                   kb, ai, analytics, escalation, csat, teams, business_hours, gdpr
├─ handlers/        user/ · admin/ · topic/ · system/
├─ middlewares/     logging, admin_guard, blocked, cooldown, i18n, rbac,
│                   rate_limit, tracing
├─ ui/              primitives (card / progress / blockquote), templates,
│                   themes, keyboards
├─ plugins/         loader + registry + builtin/*
├─ tasks/           scheduler + periodic jobs
├─ api/             FastAPI app (routes, deps, security)
├─ utils/           text, time, ids, retry, crypto, phone, validation
└─ locales/         en.yaml, ru.yaml, es.yaml, …
```

- **Architecture overview** → [docs/architecture/overview](https://davdxpx.github.io/XTV-SupportBot/architecture/overview/)
- **Event bus** → [docs/architecture/events](https://davdxpx.github.io/XTV-SupportBot/architecture/events/)
- **Plugin authoring** → [docs/architecture/plugins](https://davdxpx.github.io/XTV-SupportBot/architecture/plugins/)

## Documentation

The full reference lives at **[davdxpx.github.io/XTV-SupportBot](https://davdxpx.github.io/XTV-SupportBot/)**
(MkDocs Material, searchable, dark/light mode).

| Section | Pages |
|---|---|
| **Getting started** | [Install](https://davdxpx.github.io/XTV-SupportBot/getting-started/install/) · [First run](https://davdxpx.github.io/XTV-SupportBot/getting-started/first-run/) · [Configuration](https://davdxpx.github.io/XTV-SupportBot/getting-started/configuration/) |
| **Architecture** | [Overview](https://davdxpx.github.io/XTV-SupportBot/architecture/overview/) · [Plugins](https://davdxpx.github.io/XTV-SupportBot/architecture/plugins/) · [Events](https://davdxpx.github.io/XTV-SupportBot/architecture/events/) |
| **Features** | [RBAC & teams](https://davdxpx.github.io/XTV-SupportBot/features/rbac-and-teams/) · [Macros & KB](https://davdxpx.github.io/XTV-SupportBot/features/macros-and-kb/) · [AI](https://davdxpx.github.io/XTV-SupportBot/features/ai/) · [Analytics](https://davdxpx.github.io/XTV-SupportBot/features/analytics/) · [Integrations](https://davdxpx.github.io/XTV-SupportBot/features/integrations/) |
| **Operations** | [Deployment](https://davdxpx.github.io/XTV-SupportBot/ops/deployment/) · [Observability](https://davdxpx.github.io/XTV-SupportBot/ops/observability/) · [GDPR](https://davdxpx.github.io/XTV-SupportBot/ops/gdpr/) |
| **Reference** | [Environment](https://davdxpx.github.io/XTV-SupportBot/reference/env/) · [REST API](https://davdxpx.github.io/XTV-SupportBot/reference/api/) |

Root-level documents:

- [SETUP.md](SETUP.md) — step-by-step first-run walkthrough
- [CHANGELOG.md](CHANGELOG.md) — release notes in *Keep a Changelog* format
- [CONTRIBUTING.md](CONTRIBUTING.md) — PR, branch and commit conventions
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community expectations
- [SECURITY.md](SECURITY.md) — responsible-disclosure process

## Roadmap

v0.9 is stabilising the public-pre-release surface. Several subsystems
are already in place and will keep hardening toward **v1.0**:

- Onboarding panel rework (`/start` = home card, `/home`, `/faq`, `/settings`) — default
- Automation rules engine (if-this-then-that over ticket events) — default
- Project templates (seed a new project with macros / KB / routing / SLA) — default
- Menu-first admin UX (`/admin` tabs + inline menus for Teams / API keys) — default
- Agent cockpit (`/inbox` with saved filters + bulk actions) — gated on `FEATURE_AGENT_INBOX`
- REST API write endpoints (reply / close / assign via HTTP) — default

See the [CHANGELOG](CHANGELOG.md) for what already shipped, and
[GitHub Issues](https://github.com/davdxpx/XTV-SupportBot/issues) for
what's being discussed next.

## Security

- Every admin action is written to an audit log with configurable TTL
- Inbound link / phishing scanner is on by default; abusers are auto-muted
- API keys are SHA-256-hashed at rest — the plaintext is shown exactly once
- Outbound webhook deliveries are HMAC-SHA-256 signed
- Secret rotation helper: `python scripts/rotate_secrets.py`

Report vulnerabilities privately — see **[SECURITY.md](SECURITY.md)**.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for
the branch / commit / PR conventions and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations.

Common local tasks:

```bash
ruff check .         # lint
ruff format .        # auto-format
pytest               # run tests
mkdocs serve         # preview the docs site locally
```

CI on every push runs `lint`, `test`, `test-web` and `docker-build` — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Community & support

- **Docs site** — [davdxpx.github.io/XTV-SupportBot](https://davdxpx.github.io/XTV-SupportBot/)
- **Bot channel** — [@XTVbots](https://t.me/XTVbots)
- **XTV Network** — [@XTVglobal](https://t.me/XTVglobal)
- **Backup channel** — [@XTVhome](https://t.me/XTVhome)
- **Maintainer** — [@davdxpx](https://t.me/davdxpx) on Telegram
- **Issues** — [github.com/davdxpx/XTV-SupportBot/issues](https://github.com/davdxpx/XTV-SupportBot/issues)

## License & credits

Source-available under the **𝕏TV Public License** — see [LICENSE](LICENSE).
For licensing inquiries, reach out on Telegram
[@davdxpx](https://t.me/davdxpx).

Developed by **𝕏0L0™** ([@davdxpx](https://t.me/davdxpx)) for the
[𝕏TV Network](https://t.me/XTVglobal).

<div align="center">
<sub>© 2026 XTV Network Global · <a href="https://t.me/XTVglobal">@XTVglobal</a></sub>
</div>
