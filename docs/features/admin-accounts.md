# Admin accounts

The admin web console supports **real accounts** — a username and password
per human, with a revocable server-side session — alongside the legacy
API-key login. An account is only a way to *authenticate*; *authorization*
is read from the existing [Role/Team system](rbac-and-teams.md), keyed by
the account's linked Telegram `user_id`. There is no second permission
model.

## Why

Previously the only desktop login was pasting an API key, and **any** valid
key was treated as full admin. That meant no per-person identity, no audit
trail, and no way to revoke one person without breaking the shared key.
Real accounts fix all three: each login is a named human, bound to a
Telegram identity whose Role governs what they can do.

## The three auth paths

The API accepts, in this precedence order:

1. **Telegram Mini-App `initData`** — ordinary end users in the Mini-App.
2. **Admin session cookie** — a logged-in `AdminAccount` (this feature).
3. **`Authorization: Bearer` API key** — legacy / scripts / webhooks.

A logged-in account's permissions come from
`resolve_role(telegram_user_id)` (ADMIN_IDS-aware). **AGENT and above**
may open the console; finer per-route checks map each API scope to a
minimum Role.

## Inviting a new admin

Registration is invite-only — it consumes a single-use **registration
key** minted by an existing admin from the bot. The key is bound to the
*invitee's* Telegram identity (not the issuer's), so the new account
inherits that person's Role.

From an admin DM with the bot:

```
/apikey invite <telegram_user_id> [label]
```

…or run `/apikey invite` while **forwarding a message from the new admin**
(the bot reads their id from the forward; if their privacy hides it, fall
back to the numeric id). The same flow is available as the **🎟 Invite
admin** button in the `/apikey` menu.

The bot replies once with the invite key. Hand it to the new admin — they
register with it at the console's **"Create your account"** screen
(`/register`). On success the key is **permanently burned**: it can never
register a second account, nor be used as a bearer token.

> Registration keys carry no API scopes — they exist only to create one
> account and are dead the moment they're redeemed.

## Bootstrapping a fresh deployment

Anyone in `ADMIN_IDS` can run `/apikey invite` immediately — bot command
access is gated on `ADMIN_IDS` directly, independent of the `roles`
collection, and `resolve_role` treats `ADMIN_IDS` members as at least
`Role.ADMIN`. So the very first admin invites themselves
(`/apikey invite <their own id>`), registers, and is in.

## Logging in

The console's primary form is username + password (`POST /api/v1/auth/login`),
which sets the session cookie. The legacy **"Log in with an API key
instead"** path is still present, demoted below the primary form, and works
exactly as before — existing deployments are never locked out.

## Managing accounts

Owners/admins get an **Accounts** section in the console (and
`GET /api/v1/auth/accounts`) listing every account with its resolved Role
and last login. **Disable** soft-deactivates an account and immediately
revokes all of its live sessions (it stops working on the very next
request, not at session expiry). **Enable** reverses it. There is no
deletion — disable is reversible and sufficient.

A disabled account learns nothing at the login screen: unknown username,
wrong password, and disabled account all return the same generic
"invalid credentials" error, so the endpoint leaks no account existence or
status.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Redeem an invite key + create an account (logs in) |
| `GET` | `/api/v1/auth/check-username` | Live availability check (UX) |
| `POST` | `/api/v1/auth/login` | Username/password → session cookie |
| `POST` | `/api/v1/auth/logout` | Revoke the session + clear the cookie |
| `POST` | `/api/v1/auth/change-password` | Change own password (verifies current, revokes all other sessions, re-issues the caller's) |
| `GET` | `/api/v1/auth/accounts` | List accounts (admin/owner) |
| `POST` | `/api/v1/auth/accounts/{id}/disable` | Disable + kill sessions |
| `POST` | `/api/v1/auth/accounts/{id}/enable` | Re-enable |

See [API authentication](../reference/api-auth.md) for the key model and
[Environment reference](../reference/env.md) for the session settings.

## Security notes

- Passwords are hashed with **Argon2id** (`argon2-cffi`); plaintext and
  hashes are never logged.
- Session tokens are random (`secrets.token_urlsafe(32)`) and stored only
  as a SHA-256 hash — a DB leak hands out no live sessions.
- Login is rate-limited per IP+username (in-process; see the API auth doc
  for the scale-out caveat).
