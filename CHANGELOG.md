# Changelog

All notable changes to **XTV-SupportBot** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enterprise folder layout (domain / infrastructure / plugins / api / locales) — *Phase 2*
- Plugin system with event bus, DI container, feature flags — *Phase 3*
- i18n (YAML locales, runtime-switchable) — *Phase 4*
- RBAC + teams + queue routing — *Phase 5*
- Macros and Knowledge Base — *Phase 6*
- AI assistance via LiteLLM (drafts, summaries, sentiment, smart-routing, translation) — *Phase 7*
- Escalation rules, CSAT, business hours, holidays — *Phase 8*
- Analytics dashboard + digests + exports — *Phase 9*
- Webhooks + Discord/Slack/email bridges — *Phase 10*
- REST API (FastAPI) + React/Vite SPA web admin — *Phase 11*
- GDPR tooling + link/phishing scanner + CAPTCHA plugin — *Phase 12*
- Prometheus metrics + OpenTelemetry tracing + health endpoints — *Phase 13*
- Multi-stage Dockerfile, docker-compose, Helm chart, k8s manifests — *Phase 14*
- MkDocs-Material docs site + GitHub Actions CI/CD — *Phase 15*

## [0.9.0] — Pre-Release

First public pre-release of XTV-SupportBot. Rebranded from the internal
`xtvfeedback-bot` codebase (v2.0.0 internal). Counter reset to 0.9.0 to signal
the run-up to a stable 1.0 public release.

### Added
- Project metadata for open-source distribution (license, classifiers, URLs)
- `.github/` scaffolding (issue templates, PR template, CODEOWNERS, Dependabot)
- `CHANGELOG.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`

### Changed
- Package renamed `xtvfeedback-bot` → `xtv-support`
- Repository renamed `xtvfeedback-bot` → `XTV-SupportBot`

### Preserved from internal v2.0.0
- Forum-topic tickets with live header card
- Assignment, tags, priority, SLA, auto-close
- Anti-spam cooldown, blocked-user list
- Broadcast with pause/resume/cancel
- Project & contact-link management
- Audit log with TTL retention

---

Developed by @davdxpx
