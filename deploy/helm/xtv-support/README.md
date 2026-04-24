# xtv-support Helm chart

Install:

```bash
kubectl create secret generic xtv-support-secrets \
  --from-env-file=.env

helm install xtv-support deploy/helm/xtv-support \
  --set image.tag=0.9.0
```

Upgrade:

```bash
helm upgrade xtv-support deploy/helm/xtv-support \
  --set image.tag=0.9.1
```

## Values reference

See `values.yaml`. The chart is deliberately minimal for v0.9 —
single-replica `Deployment`, one `Service`, optional `Ingress` in a
later phase. Pyrofork's single-session constraint means multi-replica
requires external session brokering and is **not** solved by simply
bumping `replicaCount`.

Developed by @davdxpx
