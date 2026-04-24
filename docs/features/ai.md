# AI features

Opt-in, provider-agnostic AI through LiteLLM. Every feature is a
plugin gated on its own `FEATURE_AI_*` flag.

| Plugin | Flag | Trigger | Output |
|---|---|---|---|
| Reply-draft | `FEATURE_AI_DRAFTS` | `/draft` in topic | Expandable blockquote with draft |
| Ticket summary | `FEATURE_AI_SUMMARY` | `TicketClosed` event | `tickets.ai_summary` |
| Sentiment | `FEATURE_AI_SENTIMENT` | `MessageReceived` | `tickets.sentiment` |
| Smart routing | `FEATURE_AI_ROUTING` | `TicketCreated` | `tickets.ai_suggested_team` |
| Translate | `FEATURE_AI_TRANSLATE` | `MessageReceived` (lang mismatch) | `tickets.translations[]` |
| Transcribe | `FEATURE_AI_TRANSCRIBE` | `MessageReceived` with media | `tickets.transcriptions[]` |
| KB-drafter | `FEATURE_AI_KB_DRAFTER` | `/ai kb-draft` | Draft KB article |

## Configuration

```env
AI_ENABLED=true
AI_MODEL_DEFAULT=anthropic/claude-sonnet-4-5
AI_MODEL_FAST=anthropic/claude-haiku-4-5
AI_MODEL_VISION=anthropic/claude-sonnet-4-5
AI_MODEL_TRANSCRIBE=openai/whisper-1
AI_PII_REDACTION=true          # scrub CC/SSN/email/phone before send
ANTHROPIC_API_KEY=...
# OPENAI_API_KEY, GEMINI_API_KEY also picked up automatically by LiteLLM
```

## PII redaction

When `AI_PII_REDACTION=true` the redaction service removes credit
cards / SSNs / API-key-shaped tokens and hashes emails / phones to
stable short tokens before the prompt leaves the process. Turn it
off only when you trust the provider path end-to-end (on-prem
Ollama, private Azure OpenAI, etc.).

## Cost tracking

Every call writes a row to `ai_usage` (feature, model, tokens,
cost_usd, user_id, ticket_id, ts). The Phase-9 digest + Prometheus
metrics report these without extra wiring.
