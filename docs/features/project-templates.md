# Project templates

A **template** is a declarative bundle that seeds a new project with
sensible defaults — welcome card, macros, KB articles, routing rules,
SLA overrides, CSAT config, default priority / tags, feature-flag
overrides, post-install hint.

## Why

Creating a project blank means remembering to configure every
subsystem for every new project. 90% of projects fit one of a handful
of shapes (generic support, feedback, billing, VIP, dev/GitHub,
contact form, community). Templates encode that institutional
knowledge so a fresh project is useful in seconds.

## Built-in templates

| Slug | Name | Highlights |
|---|---|---|
| `support` | Technical Support | Safe default — 4 macros, 3 KB stubs, standard SLA |
| `feedback` | Feedback & Feature Requests | Low-priority default, no SLA, auto-close 30d |
| `contact` | Contact Form | Single inbox, no team routing |
| `billing` | Billing & Payments | 30m warn / 60m breach SLA, refund/VIP macros, CSAT on |
| `dev_github` | Developer Bug Reports | repro/expected/actual/env intake, GitHub webhook pre-wired |
| `vip` | VIP / White-glove | 10m warn / 15m breach, CSAT required, VIP team routing |
| `community` | Community & Discussion | KB gate on, low priority, auto-close 7d |

Run `/templates` in the admin DM to see them live with icons and
descriptions, or fetch them via the API
(`GET /api/v1/projects?active=true` for *installed* projects; the
registry itself is read-only code).

## Installing a template

Two interfaces, identical effect:

### Telegram

```
/project_template billing pay Payments
```

Arguments:

1. `template_slug` — which template (`/templates` to browse)
2. `project_slug` — the new project's identifier (must be unique)
3. `project_name` — (optional) human-readable name

### API

```bash
curl -X POST $BASE/api/v1/projects \
     -H "Authorization: Bearer $XTV_KEY" \
     -H "Content-Type: application/json" \
     -d '{"template_slug": "billing", "project_slug": "pay", "name": "Payments"}'
```

Response includes counts for each seeded subsystem:

```json
{
  "ok": true,
  "project_id": "…",
  "template_slug": "billing",
  "macros_seeded": 3,
  "kb_articles_seeded": 2,
  "routing_rules_seeded": 3
}
```

## What a template installs

A :class:`ProjectTemplate` is a frozen dataclass with the following
fields — all optional unless stated:

| Field | Notes |
|---|---|
| `slug`, `name`, `description` | Required metadata |
| `icon` | Single emoji for the grid view |
| `project_type` | `support` \| `feedback` \| `contact` |
| `welcome_card_title` / `_body` | Rendered to the user on their first ticket |
| `intake_fields` | Future: dynamic form fields in the KB gate |
| `macros` | `MacroSeed(name, body, tags, team_scope)` |
| `kb_articles` | `KbSeed(slug, title, body, tags, lang)` — slug is prefixed with `<project_slug>__` to avoid collisions |
| `routing_rules` | Match tag / priority / type → weighted team slug |
| `sla_overrides` | Per-project warn / breach minutes (overrides global) |
| `csat_enabled` / `csat_required` | Post-close survey config |
| `default_priority`, `default_tags` | Applied to every ticket in this project |
| `feature_flag_overrides` | Written to the project doc; live-toggle in a later phase |
| `post_install_hint` | Short string printed after install |

All built-ins live under
`src/xtv_support/services/templates/builtins/<slug>.py` — read them as
worked examples.

## Authoring a custom template

In a plugin:

```python
from xtv_support.services.templates import ProjectTemplate, default_registry, MacroSeed

MY_TEMPLATE = ProjectTemplate(
    slug="onboarding",
    name="Customer onboarding",
    description="New-customer concierge queue",
    icon="🚀",
    project_type="support",
    macros=(
        MacroSeed(
            name="welcome",
            body="Welcome aboard, {user_name}! Here's what to do next…",
            tags=("greeting", "onboarding"),
        ),
    ),
    default_priority="high",
    default_tags=("onboarding",),
)

default_registry.register(MY_TEMPLATE)
```

Plugins registered via the plugin loader auto-appear in
`/templates` and are installable via the API the same way as built-ins.

## Backfill of legacy projects

Projects created before the template system existed are tagged
`template_slug: "legacy"` by the migration that ships with Phase 4.2.
This lets analytics and the admin panel group by origin without
special-casing.

## Relation to routing + SLA

A template's `routing_rules` and `sla_overrides` seed the project
document. They're picked up by the existing
`services/teams/routing.py` dispatcher and `services/sla/service.py`
calculator — no parallel code path.

## Events

`ProjectTemplateInstalled` fires on success with the install counts.
`ProjectTemplateFailed` fires on error. Both are hookable via the
event bus — the audit-log plugin and analytics rollup already consume
them.
