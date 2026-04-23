# Contributing to XTV-SupportBot

Thanks for considering a contribution. This project is source-available under
the **XTV Public License** — read `LICENSE` before submitting code; your
contribution will be accepted under the same terms.

## Quick start

```bash
git clone https://github.com/davdxpx/XTV-SupportBot.git
cd XTV-SupportBot

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

pre-commit install
cp .env.example .env   # fill in test credentials for a throw-away bot
```

Run the test suite:

```bash
pytest
```

Run the linter and type-checker:

```bash
ruff check .
ruff format --check .
mypy app
```

## How to propose a change

1. **Open an issue first** for anything non-trivial — a bug report, a
   feature proposal, or a refactor RFC. Small fixes and doc typos can skip
   this step.
2. Fork the repo, create a topic branch: `feat/<short-description>`,
   `fix/<short-description>`, or `docs/<short-description>`.
3. Write the change. Keep commits focused; one commit per logical step.
4. Add or update tests — everything that changes behaviour needs coverage.
5. Update `CHANGELOG.md` under `## [Unreleased]`.
6. Push and open a pull request against `main`. Fill in the PR template.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/).

```
feat(tickets): add bulk-close command for admins
fix(sla): stop counting paused-team hours toward SLA
docs(setup): clarify forum-topic permission list
refactor(core): split router into command/callback modules
test(cooldown): cover sliding-window edge cases
```

Scopes mirror the top-level package directories: `tickets`, `projects`,
`broadcast`, `sla`, `core`, `ui`, `plugins`, `api`, …

**Do not** reference sessions, tools, or AI assistants in commit messages.
End each commit body with `Developed by @davdxpx` **or nothing** — no other
trailers.

## Code style

- Python 3.12, type hints on every public function
- `ruff` handles formatting — 100-char line length — do not reformat by hand
- Keep modules small; prefer many short files over one long one
- No dead code, no commented-out code, no `# TODO` without an issue link
- Logging: `structlog` only, use event-name strings (`log.info("ticket.created", id=…)`)

## Tests

- Unit tests under `tests/unit/` — no network, no DB
- Integration tests under `tests/integration/` — spin up `mongomock` / `fakeredis`
- End-to-end tests under `tests/e2e/` — disabled by default, opt-in with `-m e2e`
- Coverage floor: **80 %**. CI blocks below that.

## Plugin contributions

A **plugin** lives under `src/xtv_support/plugins/<plugin_name>/` and
implements the `BasePlugin` hooks. If the plugin brings new dependencies,
declare them under a new optional-dependency group in `pyproject.toml`. See
`docs/plugins/authoring.md` for the authoring guide (added in Phase 15).

## Releases

Maintainer-only.

1. `CHANGELOG.md`: move entries from `[Unreleased]` into a new version block
2. Bump `version` in `pyproject.toml` and `src/xtv_support/version.py`
3. Tag: `git tag -s vX.Y.Z -m "Release vX.Y.Z"`
4. Push: `git push origin main --tags`
5. GitHub Actions builds and publishes the release

---

Developed by @davdxpx
