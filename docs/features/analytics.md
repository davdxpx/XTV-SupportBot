# Analytics + reporting

## Nightly rollup

A scheduler task writes one document per UTC day into
`analytics_daily` with ticket volume, first-response + resolution
medians and p90s, SLA compliance. Dashboards + digests query the
rollup collection instead of the raw `tickets` scan.

## Weekly digest

Enable `FEATURE_ANALYTICS_DIGEST=true` — every 7 days the bot posts
into the admin topic (or `DIGEST_TOPIC_ID` if set):

- Total tickets across the window
- SLA compliance percentage (% met)
- Median first-response average (weighted)
- Median resolution average (weighted)
- Top 3 projects + teams by volume

## Exports

```
/export csv 30    # tickets of the last 30 days, CSV attachment
/export json 30   # same content as a JSON document
```

Columns are stable (`COLUMNS` in `xtv_support.services.analytics.exporter`)
so third-party dashboards can consume them directly.

## REST access

```
GET /api/v1/analytics/summary?days=7
```

Requires the `analytics:read` scope on the API key.
