# Integrations

## Outgoing webhooks

HMAC-SHA-256-signed POSTs with retry backoff (5s → 30s → 2m → 10m →
1h, then disable). Headers:

- `X-XTV-Signature: sha256=<hex>`
- `X-XTV-Event: <event_name>`
- `X-XTV-Delivery: <uuid4>`
- `X-XTV-Timestamp: <epoch>`

Receivers verify via
`xtv_support.services.webhooks.signer.verify(body, secret, signature)`.

## Discord bridge

`FEATURE_DISCORD_BRIDGE=true` + `DISCORD_WEBHOOK_URL=...` — ticket
events appear as coloured embeds in the target channel.

## Slack bridge

`FEATURE_SLACK_BRIDGE=true` + `SLACK_WEBHOOK_URL=...` — events
rendered via Slack Block-Kit with colour-coded attachments.

## Email ingestion

v0.9 ships scaffolding (feature flag + plugin skeleton). Full
IMAP/SMTP pipeline lands in v0.10.
