# Working on XTV-SupportBot

## Language & tone
- Respond in **German (du-form)** by default. Code, commit messages, PR
  descriptions, and docs stay in English.
- Tight, direct. No long prose. No preamble like "Ich werde jetzt…" —
  just do it and report the result.
- When something I shipped broke: admit it plainly, explain the root
  cause, fix it. No "Lass mich überlegen ob…" — just fix.

## PR workflow (learned the hard way)
- **Always `base=main`.** Never stack PRs on each other. One merge-chain
  accident and three phase-PRs got stranded on intermediate branches —
  never again.
- One PR per self-contained change. Small PRs ship faster than big ones.
- CI is the source of truth, not my local env — my local `cryptography`
  sometimes panics on import, not relevant to Railway/CI.
- Open the PR via `mcp__github__create_pull_request`, short body, no
  session links.

## Commit conventions
- Author identity on every commit: `𝕏0L0™ <davdxpx@gmail.com>` (via
  `git -c user.name=… -c user.email=…`). **Never** "Claude", "Anthropic",
  or `Co-Authored-By:`.
- Footer: empty or `Developed by @davdxpx`. Nothing else — no session
  links, no "Generated with Claude Code".
- Commit message body: short, WHY not WHAT, minimal prose.

## Code style
- **Default to no comments.** Only when the WHY is non-obvious (hidden
  constraint, subtle invariant, workaround for a specific bug).
- No "added for the X flow / used by Y" comments — those rot.
- No multi-paragraph docstrings; one short line max if needed.
- No feature flags or back-compat shims when we can just change the code.
- No error handling / fallbacks for scenarios that can't happen. Trust
  internal code; validate only at system boundaries.

## Design & UX preferences
- CSS custom properties for tokens (colours, radii, shadows) in
  `web/src/styles/theme.css`. Dark-first with `prefers-color-scheme`
  fallback to light.
- Telegram Mini-App: mirror `Telegram.WebApp.themeParams` onto the same
  `--tg-*` variables at boot so the Mini-App follows the user's client
  theme automatically.
- Animations + loading states are **required**, not polish:
  - Skeleton shimmers while data fetches
  - Spinner on every busy button
  - `fade-in` / `pop-in` entrance animations on tiles / bubbles / rows
  - `@media (prefers-reduced-motion: reduce)` override always present
- Mobile-responsive is required. Sidebar → horizontal tab scroll under
  768px. Two-column detail layouts stack under 900px.
- Inline styles only for one-off tweaks. Reusable patterns live in
  `theme.css` as classes (`.btn`, `.card`, `.chip`, `.pill`, `.stat`,
  `.tile`, `.bubble`, `.data-table`, …).

## Docs policy — non-negotiable
- Whenever an env var, API endpoint, scope, feature, or config surface
  changes, update the docs in the SAME PR:
  - `docs/reference/env.md` for env vars
  - `docs/reference/api.md` / `api-write.md` for endpoints
  - `docs/reference/api-auth.md` for scopes
  - `docs/features/<area>.md` for feature writeups
  - `docs/ops/*.md` for deploy / ops guides
  - `docs/index.md` feature tour
  - `mkdocs.yml` nav if new pages
- No "use the bot with /admin" placeholders. If a feature is promoted
  to the web, the docs must reflect that the web UI is fully functional.

## Web/API architecture
- REST API is FastAPI, mounted at `/api/v1/*` in the same process as
  the Telegram bot (`xtvsupport.up.railway.app`).
- React SPA (`web/`) builds to `web/dist/` and is served at `/`.
  `index.html` fallback for all non-API paths (React-Router deep links).
- Dual-mode UI: `UI_MODE=chat|webapp|hybrid` — `chat` is the default,
  `webapp` uses Telegram Mini-App signed `initData`, `hybrid` renders
  both. Per-user override via `users.ui_pref`.
- Auth: Admin-SPA → `Authorization: Bearer xtv_…` API key.
  Telegram Mini-App → `X-Telegram-Init-Data` HMAC validated against
  `BOT_TOKEN`. Unified via `current_tg_user_or_apikey` where needed.

## FastAPI gotchas (learned in prod)
- `from __future__ import annotations` turns type hints into strings
  that FastAPI resolves via `get_type_hints()`. If `Request` (or any
  dep type) is only imported under `if TYPE_CHECKING:`, resolution
  fails silently and FastAPI classifies the parameter as a query
  field → 422 `{"loc":["query","request"]}`. **`Request` must be a
  module-level import** in every file that uses `request: Request`
  (deps.py, auth_webapp.py, routes/me.py).
- Frozen dataclass as a `Depends()` return with type annotation
  (`user: TelegramUser = Depends(...)`) can confuse FastAPI into
  treating the dataclass as a request body schema. Prefer
  `Annotated[TelegramUser, Depends(...)]` — explicit and unambiguous.
- `Depends()` params without defaults must come before those with
  defaults in a route signature.

## Deploy (Railway)
- Railway auto-detects the repo-root `Dockerfile` and ignores
  `nixpacks.toml`. The root `Dockerfile` is a **multi-stage build**:
  `node:20-slim` builds `web/dist/`, `python:3.12-slim` installs deps,
  final stage has both (`/app/web/dist/` + `/install/`).
- `npm ci --no-audit --no-fund` in the web stage. No BuildKit
  `--mount=type=cache` — Railway's builder rejects it.
- Persistent volume mounted at `/data`, `SESSION_DIR=/data`.
  Otherwise the pyrofork session gets wiped on every deploy and
  Telegram rate-limits `auth.ImportBotAuthorization` with
  `FLOOD_WAIT_X` (up to 11+ min).
- `_start_client_with_floodwait` wraps `client.start()` — catches
  `FloodWait`, idles for the requested seconds + 5s pad, retries up
  to 3× instead of crashing (which would extend the ban).
- WebApp menu-button: HTTP Bot API (`setChatMenuButton`), **not**
  pyrofork raw MTProto — `BotMenuButtonWebApp` isn't re-exported in
  every pyrofork layer we ship.

## Testing policy
- New routes / dep chains get regression tests, especially 422 guards
  (FastAPI classifier bugs are silent; only tests catch them).
- Tests live under `tests/unit/` — pure unit when possible, TestClient
  when a full app is needed.
- Fixtures that monkey-patch `settings_mod.settings` must restore it
  on teardown (`yield` + reassign saved value) so downstream tests
  aren't polluted.
- Local env can be broken (pymongo/cryptography quirks). If lint +
  tests I wrote pass and the touched module compiles, push and let
  CI be the judge.

## Work cadence
- Stepwise to avoid context timeouts. Read the specific files needed,
  don't spelunk the whole repo.
- After a change: lint, format, run the affected tests, push. Don't
  batch up half-finished work.
- When a live deploy is borked, investigate the logs carefully before
  touching code — the build timestamp often proves which commit is
  actually running.

## Stuff I should not mention
- The `/home/user/XTV-SupportBot/plans/` folder (if it ever exists
  again) is my scratch; don't reference session history or prior
  plans in commits / PRs / docs.
- Claude / Anthropic / agent footers in any generated artefact.
