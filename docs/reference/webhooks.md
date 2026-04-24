# Outgoing webhooks

Subscribe to real-time events from the bot. Every POST is signed with
HMAC-SHA-256 so consumers can verify authenticity without pulling any
state from the bot.

## Event catalogue

| Event name | When |
|---|---|
| `ticket.created` | A user just opened a new ticket |
| `ticket.assigned` | An agent was assigned (or unassigned: `assignee_id: null`) |
| `ticket.tagged` | A tag was added or removed |
| `ticket.priority_changed` | Priority changed |
| `ticket.closed` | Ticket moved to closed |
| `ticket.reopened` | Ticket came back to open |
| `ticket.sla_warned` | SLA warn-threshold crossed |
| `ticket.sla_breached` | SLA breach-threshold crossed |
| `rule.executed` | An automation rule fired |
| `project_template.installed` | A template seeded a fresh project |

Subscribe to a subset via the `events` array on `POST /api/v1/webhooks`;
pass `[]` to receive every event.

## Delivery envelope

Each delivery is a POST to your registered URL with:

**Headers**

```
Content-Type: application/json
X-XTV-Event: ticket.closed
X-XTV-Delivery: 3e95f8c5-…        ← UUID, stable per delivery
X-XTV-Timestamp: 1714048800       ← Unix seconds, signed
X-XTV-Signature: sha256=<hex>     ← HMAC-SHA-256 of the body
```

**Body** — one JSON object per event. The shape mirrors the internal
domain event with a few helpful extras:

```json
{
  "event": "ticket.closed",
  "delivered_at": "2026-04-24T12:00:00Z",
  "ticket_id": "652…",
  "closed_by": 123,
  "reason": "resolved"
}
```

## Signature verification

Compute `HMAC-SHA-256(body, secret)` in hex and compare with
`X-XTV-Signature` (strip the `sha256=` prefix).

=== "Python"

    ```python
    import hmac, hashlib

    def verify(body: bytes, header_sig: str, secret: str) -> bool:
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        received = header_sig.removeprefix("sha256=")
        return hmac.compare_digest(expected, received)
    ```

=== "Node"

    ```javascript
    const crypto = require("node:crypto");

    function verify(body, headerSig, secret) {
      const expected = crypto
        .createHmac("sha256", secret)
        .update(body)
        .digest("hex");
      const received = headerSig.replace(/^sha256=/, "");
      return crypto.timingSafeEqual(
        Buffer.from(expected),
        Buffer.from(received),
      );
    }
    ```

=== "Go"

    ```go
    func Verify(body []byte, headerSig, secret string) bool {
        mac := hmac.New(sha256.New, []byte(secret))
        mac.Write(body)
        expected := hex.EncodeToString(mac.Sum(nil))
        received := strings.TrimPrefix(headerSig, "sha256=")
        return hmac.Equal([]byte(expected), []byte(received))
    }
    ```

## Retry policy

- 3 attempts with exponential backoff (2s, 6s, 30s).
- Any response status `2xx` is considered delivered.
- Non-2xx or connection failure → retry.
- After the third failure the delivery is marked failed and logged.
  Re-delivery is manual (via a planned admin UI; the hook stays
  subscribed so *future* events keep firing).

## Replay protection

`X-XTV-Timestamp` is part of the signed payload — reject deliveries
more than a few minutes old to block replay attacks. Suggested window:
5 minutes.

## Pitfalls to avoid

- **Secret in URL.** Don't encode the secret into the URL path; use
  the provided HMAC header.
- **Body mutation.** Your framework may pre-parse JSON and strip
  whitespace — compute the HMAC on the raw bytes.
- **IPs.** Don't allow-list source IPs. Railway / Render rotate egress
  IPs; the signature is the source of truth.

## Managing subscriptions

See [API write endpoints → Webhooks](api-write.md#webhooks) for the
full CRUD surface.
