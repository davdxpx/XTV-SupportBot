# Changelog

All notable changes to **XTV-SupportBot** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes. See v0.9.0 below._

## [0.9.0] — 2026-04-23

First public pre-release of **XTV-SupportBot**. Rebranded from the internal
`xtvfeedback-bot` codebase (v2.0.0 internal) and reset to 0.9.0 to signal the
run-up to a stable 1.0 public release.

### Added — Open-source scaffolding
- `pyproject.toml` with optional-dependency groups (`redis`, `ai`, `api`,
  `storage`, `observability`, `dev`, `all`) and full classifiers.
- `LICENSE` (XTV Public License — placeholder body until operator text lands).
- `.github/` scaffolding: issue templates, PR template, CODEOWNERS, Dependabot.
- `CHANGELOG.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`.
- `.editorconfig`, `.gitattributes`, `Makefile`, pre-commit config.

### Added — Enterprise folder layout
- `src/xtv_support/` package with `config/`, `core/`, `domain/`,
  `infrastructure/`, `services/`, `handlers/`, `middlewares/`, `ui/`,
  `plugins/`, `tasks/`, `api/`, `utils/`, `locales/`.
- `deploy/`, `docs/`, `scripts/`, `tools/`, `tests/{unit,integration,e2e}/`
  at the top level.
- `git mv` migration preserves history; every `app.*` import rewritten to
  `xtv_support.*`.

### Added — Core kernel (Phase 3)
- `Container` (typed DI with cycle detection).
- `EventBus` (async pub/sub, error-isolated, optional base-class propagation).
- `StateMachine` over a pluggable `StateStore` (in-memory for now, Redis
  adapter staged).
- `PluginLoader` + `PluginRegistry` with built-in discovery + entry-point
  discovery + feature-flag gating. 12 built-in plugins ship with v0.9.
- `FeatureFlags` (17 `FEATURE_*` flags, Pydantic-settings backed).

### Added — i18n (Phase 4)
- `I18n` + YAML loader + per-user `/lang` command.
- 11 locales shipped: en (full), ru, es, hi, bn, ta, te, mr, pa, gu, ur.
- Fallback chain: user preference → telegram `language_code` → `DEFAULT_LANG`.

### Added — RBAC + Teams (Phase 5)
- 6-level role hierarchy: user / viewer / agent / supervisor / admin / owner.
- `/role` and `/team` admin commands; `/queue` and `/mytickets` for agents.
- Declarative queue routing with team-scoped rules (tag / project_id /
  project_type / priority matchers, weighted).
- `TicketRoutedToTeam` event on the bus.

### Added — Macros + Knowledge Base (Phase 6)
- Macros: `/macro save|use|list|show|del` inside topics, scoped per team
  or global, placeholder substitution.
- KB: `/kb add|edit|del|list|show|search`, MongoDB text index with
  weighted fields, helpfulness counters.
- Pre-ticket gate: new-user messages matched against KB before a ticket is
  created; `/humanplease` to bypass.

### Added — AI (Phase 7)
- `AIClient` over LiteLLM (provider-agnostic). Opt-in via `AI_ENABLED`.
- 7 feature plugins: reply drafts, summary, sentiment, smart routing,
  translation, image OCR (voice staged), KB drafter. Each behind its own
  `FEATURE_AI_*` flag.
- PII-redaction pipeline (CC/SSN/API-key removal + hashed email/phone).
- Cost tracking into `ai_usage` collection.

### Added — Escalation + CSAT + Business Hours (Phase 8)
- Timezone-aware business-hours clock with holiday support; SLA can
  pause during closed hours.
- Declarative escalation rules matched on events with tag/priority/
  project filters.
- CSAT 1–5★ persistence + aggregate stats (promoters, detractors,
  promoter-share).

### Added — Analytics + Reporting (Phase 9)
- Pure aggregators: ticket volume, first-response + resolution medians
  and p90s, SLA compliance, agent leaderboard with optional CSAT.
- Nightly rollup task into `analytics_daily`.
- CSV + JSON exporters with a stable column contract.
- Weekly digest plugin that posts into the admin topic.

### Added — Integrations (Phase 10)
- HMAC-SHA-256 webhook signer + exponential retry policy.
- Discord bridge plugin (embed colours per event type).
- Slack bridge plugin (Block-Kit attachments).
- Email-ingress plugin scaffolding (full IMAP/SMTP lands in v0.10).

### Added — REST API + Web admin (Phase 11)
- FastAPI app (`API_ENABLED=true`) with `/health`, `/ready`,
  `/api/v1/version`.
- API-key auth (SHA-256 hash + scope model: tickets/projects/users/
  analytics/webhooks/admin:full).
- Read-only routes: `/api/v1/tickets`, `/api/v1/projects`,
  `/api/v1/analytics/summary`.
- React + Vite + TypeScript SPA scaffold under `web/` with Login,
  Dashboard, Tickets pages and a typed fetch client.

### Added — GDPR + Security (Phase 12)
- `/gdpr export` (JSON bundle of user data) + `/gdpr delete` (soft-
  delete with 30-day grace + periodic hard purge).
- Link + phishing scanner (blocklist + heuristics for IP hosts,
  punycode, credential-keyword paths).
- Start-captcha plugin (HMAC-signed arithmetic challenge).
- `scripts/rotate_secrets.py` for webhook + captcha secrets.

### Added — Observability (Phase 13)
- Prometheus registry with 9 named collectors + OpenMetrics export
  at `/metrics`.
- OpenTelemetry tracer install (OTLP gRPC + HTTP) gated on
  `OTEL_EXPORTER_OTLP_ENDPOINT`.
- `/health` + `/ready` probes.

### Added — Deployment (Phase 14)
- Multi-stage Dockerfile (node-builds-SPA → python-runtime) under
  `deploy/docker/Dockerfile`.
- `docker-compose.yml` with mongo + redis + optional prometheus +
  grafana via the `observability` profile.
- Helm chart `deploy/helm/xtv-support` with templates, values,
  security context, readiness/liveness probes.
- Raw Kubernetes manifest `deploy/k8s/deployment.yaml`.
- Thin repo-root `Dockerfile` for Railway / Heroku / Nixpacks
  auto-detect.

### Added — Docs + CI/CD (Phase 15)
- MkDocs-Material documentation site (`docs/` + `mkdocs.yml`) with 5
  sections (Getting Started, Architecture, Features, Operations,
  Reference).
- GitHub Actions workflows:
    - `ci.yml` — lint + pytest with mongo/redis services + SPA build +
      docker-build on main.
    - `release.yml` — multi-arch GHCR push + GitHub Release on `v*`
      tags.
    - `docs.yml` — MkDocs → GitHub Pages deploy.
- Pre-commit config (ruff lint + format, standard hygiene hooks,
  gitleaks).

### Changed
- Package renamed `xtvfeedback-bot` → `xtv-support`; repository
  rename handled manually on GitHub.
- Schema version bumped 3 → 6 across phases 5 / 6 / 9 (roles, teams,
  macros, kb_articles, analytics_daily indexes added incrementally).

### Preserved from internal v2.0.0
- Forum-topic tickets with live header card, assignment, tags,
  priority, SLA, auto-close.
- Anti-spam cooldown, blocked-user list.
- Broadcast with pause/resume/cancel.
- Project & contact-link management.
- Audit log with TTL retention.

---

Developed by @davdxpx
