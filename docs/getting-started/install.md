# Install

## Requirements

- Python 3.12
- MongoDB 5.0+ (Atlas or self-hosted)
- A Telegram forum supergroup with the bot as admin (Manage Topics)
- `API_ID` / `API_HASH` from [my.telegram.org](https://my.telegram.org)
- Bot token from [@BotFather](https://t.me/BotFather)

## Install methods

=== "pip (local dev)"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'

    cp .env.example .env
    # fill in API_ID, API_HASH, BOT_TOKEN, MONGO_URI, ADMIN_IDS, ADMIN_CHANNEL_ID

    python main.py
    ```

=== "Docker"

    ```bash
    docker build -f deploy/docker/Dockerfile -t xtv-support:0.9.0 .
    docker run --rm --env-file .env xtv-support:0.9.0
    ```

=== "docker-compose"

    ```bash
    docker compose -f deploy/compose/docker-compose.yml up
    ```

=== "Helm"

    ```bash
    kubectl create secret generic xtv-support-secrets --from-env-file=.env
    helm install xtv-support deploy/helm/xtv-support --set image.tag=0.9.0
    ```

=== "Railway / Nixpacks"

    Repo root ships a thin Dockerfile + `Procfile` / `nixpacks.toml`.
    Push to Railway and fill the env vars in the project settings.

## Optional extras

```bash
# Redis cache + distributed cooldown
pip install -e '.[redis]'

# AI features via LiteLLM
pip install -e '.[ai]'

# REST API + React SPA
pip install -e '.[api]'

# Prometheus + OTEL
pip install -e '.[observability]'

# Everything
pip install -e '.[all]'
```
