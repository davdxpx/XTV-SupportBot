# Changelog

All notable changes to **XTV-SupportBot** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Closed ticket topics are auto-deleted (keeps the supergroup tidy):** a background sweeper deletes a ticket's forum topic once it has been closed for `TOPIC_DELETE_AFTER_CLOSE_MINUTES` (default 1440 = 24h; set `0` to disable). Closing still happens immediately; only the eventual deletion is delayed and configurable.
- **Ticket header controls stay in one message (chat cleanliness):** pressing Assign / Tag / Priority on a ticket's header card now swaps that card's own buttons to the picker in place instead of posting (and later deleting) a throwaway message. Picking an option re-renders the header and restores the default action row. **Close** now asks for confirmation first (✅ Confirm close / ◀ Back) inside the same message before closing the ticket + topic.

### Fixed
- **Web ticket replies and closes never reached the supergroup:** `POST /api/v1/me/tickets/{id}/reply` only wrote to the database and `…/close` only flipped the status — neither touched the ticket's forum topic. Both now go through the shared ticket service (bot `Client` resolved from the container), so a web reply is posted into the topic and a web close also closes the topic and notifies the user, exactly like the bot. Both degrade gracefully (bare DB write + warning) on an API-only deploy.

### Added
- **Runtime settings now drive the live consumers + bot panel parity:** the anti-spam cooldown, SLA warn deadline and brand name/tagline are resolved from the runtime settings at request time, so editing them in the console takes effect immediately (no restart). The bot's `/admin` → Settings section shows the current operational values and its feature-flag toggles now apply **live** (no more "next deploy").
- **Live runtime settings (no redeploy) + admin console Settings page:** operational knobs — SLA timers, cooldown/anti-spam, auto-close, topic auto-delete, broadcast tuning, brand strings, default UI mode/language — are now editable from a new **Settings** page in the admin console (owner/admin), backed by `GET`/`PATCH /api/v1/settings`. Values are stored as overrides on top of the env defaults and resolved live via a short-TTL cache; the auto-close and topic-cleanup sweepers already read them without a restart. An allowlist is the single source of truth for what's editable — secrets and infrastructure settings stay env-only and are never exposed.
- **Account & profile menu + mobile bottom bar in the admin console:** the sidebar footer is now a logged-in account chip (avatar from Telegram photo or coloured initials, name, role — a key glyph for legacy API-key sessions) that opens a dropdown with a **theme switch** (Auto / Light / Dark, persisted), quick links, **Account settings**, and **Log out**, replacing the bare disconnect button. The new **Account** page shows identity + theme and lets account users **change their password** (`POST /api/v1/auth/change-password`, which verifies the current password and signs out all other devices). On phones the cut-off icon rail is replaced by a proper **bottom navigation bar** (primary tabs + a full-navigation sheet + profile), respecting the safe-area inset. `GET /api/v1/me` now also reports `auth_method`.
- **Broadcast management in the web console:** a new **Broadcast** page (owner/admin only) to compose and send a message to every active user, watch live progress, and cancel a running broadcast — bringing the bot's broadcast surface to the admin SPA via new `/api/v1/broadcasts/*` routes. Sending reuses the existing one-at-a-time, FloodWait-aware `BroadcastManager` and is guarded behind a type-`SEND` confirmation.
- **Macros & Knowledge-Base management in the web console:** a new **Content** page (owner/admin only) to create/edit/delete canned macros and KB articles, via new `/api/v1/macros/*` and `/api/v1/kb/*` routes reusing the existing repositories.
- **API-key management in the web console:** a new **Keys** page (owner/admin only) to list, mint (scoped bearer keys or single-use registration invites), and revoke API keys — bringing the bot's `/apikey` surface to the admin SPA via new `/api/v1/apikeys/*` routes. The plaintext key is shown exactly once at creation.
- **RBAC management in the web console:** a new **Access** page (owner/admin only) to grant/revoke user roles and create/delete teams + manage members — bringing the bot's `/role` and `/team` surfaces to the admin SPA, backed by new `/api/v1/rbac/*` routes that reuse the existing roles/teams repositories. A caller can never grant a role above their own rank.
- **German language** (`de`) added to the bundled locales, plus a `GET /api/v1/me/languages` endpoint so the Mini-App language picker is driven by the locales that actually exist (no more dead options). Settings now show clear saving/saved feedback with a brief lockout after each change.
- **Ticket attachments (images & files):** users can attach files when opening a request from the Mini-App; the bot stores them in the admin supergroup (Telegram `file_id`, no external blob store) and the admin console streams images inline via `GET /api/v1/tickets/{id}/attachments/{index}`. New `POST /api/v1/me/tickets/{id}/attach`.
- **Single-screen New Ticket:** area selection, message, and attachments are now all on one screen instead of a multi-step flow.
- **Full project management in the web console:** click a project to open a manage screen with editable fields and a **danger zone** — archive/restore plus a permanent **purge** (hard delete). New `GET/PATCH/POST(archive|restore)/DELETE /api/v1/projects/{id}` routes, all keyed by `_id` (slug fallback).
- **Reusable in-app confirmation dialog** replacing the browser `confirm()` popup across the console (rule purge, ticket resolve, project purge), with a type-the-name guard for irreversible deletes.
- **Live ticket stats endpoint** (`GET /api/v1/tickets/stats`): open/closed/unassigned/total/today counts straight from the tickets collection, so the admin console dashboard reflects reality immediately instead of waiting on the nightly analytics roll-up.
- **Real admin accounts:** Username/password login for the admin web console, replacing API-key-as-admin. Accounts are created through a single-use "Register with API Key" invitation (`/apikey invite`) that burns the key on redemption, and are bound to the invitee's Telegram identity so permissions read from the existing Role/Team RBAC system — no second permission model. Server-side, revocable sessions (httpOnly cookie, Argon2id passwords, SHA-256-hashed session tokens); an Accounts management surface for owners/admins (list, disable/enable with immediate session revocation); login rate-limiting. The legacy `Authorization: Bearer` API-key login remains fully supported as a secondary path.
- **External User Directory:** Map user metadata from an external MongoDB database directly into SupportBot. Allows configuring conditional logic based on a user's subscription or VIP tier status dynamically. Includes a full interactive configuration wizard and UI surfacing of user priority levels across the chat interface and the Mini-App.

### Fixed
- **Mini-App ticket creation had no spam protection:** the web/Mini-App `POST /api/v1/me/tickets` path is now rate-limited by the same sliding-window cooldown the bot uses (returns `429` with `retry_after` when exceeded).
- **Project delete returned 404 for admins:** the SPA sent the project `_id` but the route keyed on `slug` (and template/bot-created projects have no slug). Project routes are now `_id`-keyed with a slug fallback, so delete/edit/archive work for every project.
- **Admin console not usable on mobile:** the Overview stat grid now reflows (4→2→1 columns), wide data tables scroll instead of breaking the layout, the header wraps, and small buttons get larger tap targets on phone widths.
- **Web tickets created no forum topic:** the Mini-App / web `POST /api/v1/me/tickets` path inserted a bare ticket document and never created the admin-supergroup forum topic + header card. Bot and web now share one ticket-creation service, so both produce an identical ticket; the web path degrades gracefully (still persists the ticket) when no bot client is available. Topic-creation failures are now logged at ERROR with the admin channel id and the real Telegram cause, instead of being silently swallowed.
- **Admin console showed 0 tickets everywhere:** the dashboard read headline counts from the (initially empty) `analytics_daily` roll-up. It now uses live counts from `GET /api/v1/tickets/stats`.
- **`GET /api/v1/me` privilege bug:** the endpoint returned `is_admin: true` for *any* valid API key regardless of scope. It now resolves the real Role for account sessions and only reports admin for API keys whose scopes actually satisfy `admin:full`.

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
