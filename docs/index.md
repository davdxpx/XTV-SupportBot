# XTV-SupportBot

Enterprise-grade Telegram support and feedback bot. Every ticket is a
Telegram forum topic in your admin supergroup, so the whole team can
collaborate on one conversation.

!!! tip "Status"
    v0.9.0 is the public pre-release. Interfaces may still change between
    minor versions; see the [Changelog](https://github.com/davdxpx/XTV-SupportBot/blob/main/CHANGELOG.md).

## Feature tour

| Area | Highlights |
|---|---|
| **Tickets** | forum-topic per ticket, SLA timers, auto-close, assignment, tags, priority |
| **Teams & RBAC** | Owner / admin / supervisor / agent / viewer; declarative queue routing |
| **Productivity** | macros, knowledge base with full-text search, pre-ticket FAQ gate |
| **AI (opt-in)** | reply drafts, summaries, sentiment, smart routing, translation, OCR |
| **Escalation & CSAT** | rules engine, business hours, holiday calendar, 1–5★ surveys |
| **Analytics** | nightly rollups, SLA compliance, agent leaderboard, CSV/JSON export, weekly digest |
| **Integrations** | HMAC-signed outbound webhooks, Discord + Slack bridges, email ingestion (scaffolding) |
| **API & Web** | FastAPI REST (API keys + scopes), minimal React + Vite admin SPA |
| **Compliance** | GDPR export/delete, link scanner, start CAPTCHA, secret rotation |
| **Observability** | Prometheus metrics, OpenTelemetry tracing, /health + /ready |
| **i18n** | English + 10 languages (Russian, Spanish, Hindi, Bengali, Tamil, Telugu, Marathi, Punjabi, Gujarati, Urdu) |

## Tech stack

- Python 3.12, async everywhere (pyrofork + motor)
- MongoDB + optional Redis
- Pydantic settings, structlog-style logging
- LiteLLM (provider-agnostic AI), FastAPI, React + Vite SPA

## Where next

- [Install](getting-started/install.md)
- [First run](getting-started/first-run.md)
- [Architecture](architecture/overview.md)
- [Plugin authoring](architecture/plugins.md)
- [Environment reference](reference/env.md)

Developed by @davdxpx
