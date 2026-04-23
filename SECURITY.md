# Security Policy

## Supported Versions

XTV-SupportBot is in pre-release. Security fixes are shipped on the latest
minor line. Older lines receive fixes only if the maintainer flags them as
`long-term`.

| Version | Supported           |
| ------- | ------------------- |
| 0.9.x   | :white_check_mark:  |
| < 0.9   | :x:                 |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security bugs.**

Contact the maintainer privately:

- Telegram: [@davdxpx](https://t.me/davdxpx)
- Email: `davdxpx@gmail.com`

Please include:

- A description of the vulnerability and the affected component
- Steps to reproduce (a minimal PoC is ideal)
- The version / commit hash you tested against
- Any known mitigations

You will receive an acknowledgement within **72 hours**. Confirmed issues are
assigned a CVE-style internal identifier, patched on a private branch, and
disclosed after a coordinated release. Reporters are credited in
`CHANGELOG.md` unless they request otherwise.

## Scope

In scope:

- Authentication / authorization bypasses (admin guard, RBAC, API tokens)
- Injection vulnerabilities (Mongo, command, template)
- Secret exposure (logs, error messages, audit records)
- Session-file mishandling
- Webhook signature forgery
- Broadcast / DM abuse paths
- Privilege-escalation via plugin loading

Out of scope:

- Self-XSS in content that only the author can see
- Denial-of-service by a privileged admin against their own instance
- Telegram-platform bugs (report those to Telegram directly)
- Vulnerabilities in third-party bridges (Discord/Slack) that exist upstream

## Hardening Recommendations for Operators

- Rotate any token that appeared in an earlier commit of `.env.example` from
  the pre-OSS history.
- Keep `ADMIN_IDS` minimal; treat it like a root password.
- Run the process as a non-root user (the Dockerfile already does).
- If you expose the REST API, put it behind a reverse proxy with TLS.
- Enable `ERROR_LOG_TOPIC_ID` so internal tracebacks never leak into user DMs.
- Subscribe this repo's releases to receive security patch notifications.

---

Developed by @davdxpx
