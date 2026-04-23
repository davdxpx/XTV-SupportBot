# Observability

## Prometheus

Set `METRICS_ENABLED=true` + `API_ENABLED=true`. Metrics appear at
`GET /metrics` in OpenMetrics text format:

- `xtv_messages_total{direction, type}`
- `xtv_tickets_total{state, project}`
- `xtv_sla_breaches_total{team}`
- `xtv_ai_tokens_total{model, feature}`
- `xtv_ai_cost_usd_total{model}`
- `xtv_webhook_deliveries_total{status}`
- `xtv_broadcast_messages_total{status}`
- `xtv_handler_duration_seconds` (histogram)
- `xtv_db_query_duration_seconds{collection}` (histogram)

docker-compose ships a Prometheus instance under the `observability`
profile (`docker compose --profile observability up`) that scrapes
the bot automatically.

## OpenTelemetry

Set `OTEL_EXPORTER_OTLP_ENDPOINT` and (optionally)
`OTEL_SERVICE_NAME`. The bot auto-installs a BatchSpanProcessor with
the OTLP exporter (`OTEL_EXPORTER_OTLP_PROTOCOL=grpc` default,
`http/protobuf` also supported). Missing packages → skip + log one
line.

## Health probes

- `GET /health` — process liveness.
- `GET /ready` — readiness including a Mongo ping.

The Helm chart wires both into the container `readinessProbe` /
`livenessProbe`.
