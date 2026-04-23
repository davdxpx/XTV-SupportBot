# XTV-SupportBot — Admin SPA

Minimal React + Vite + TypeScript scaffold that consumes the
FastAPI REST surface under `/api/v1/…`. Login by pasting an API key
generated with `/apikey create <scope>` in the bot.

## Scripts

```bash
pnpm install
pnpm dev         # http://localhost:5173, proxies /api -> :8000
pnpm typecheck
pnpm build       # emits dist/ (FastAPI mounts this at /web/)
```

## Structure

```
src/
  main.tsx          router + RequireAuth guard
  components/
    Layout.tsx      nav + logout
  pages/
    Login.tsx       paste-and-go key entry
    Dashboard.tsx   last-7-days analytics cards
    Tickets.tsx     read-only ticket table
  lib/
    api.ts          typed fetch client + localStorage key management
```

The SPA is intentionally minimal in v0.9 — the router + auth
scaffolding + two live pages give the REST surface something that
exercises every endpoint end-to-end without committing to a heavy
UI framework. Later phases (v1.x) expand into macros / KB / teams /
settings views.

Developed by @davdxpx
