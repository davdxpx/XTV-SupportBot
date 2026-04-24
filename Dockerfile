# syntax=docker/dockerfile:1.7
# Multi-stage build for XTV-SupportBot.
#
# Railway auto-detects this repo-root Dockerfile and builds it directly.
# The nixpacks.toml file is ignored when a Dockerfile is present.
#
# Stage 1 — build the React SPA so /web/dist/ exists.
# Stage 2 — install Python deps into a staging prefix.
# Final  — slim runtime with the SPA assets baked into /app/web/dist/.

# ---------------------------------------------------------------------------
FROM node:20-slim AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json web/tsconfig.json web/vite.config.ts web/index.html ./
COPY web/src ./src
RUN npm ci --no-audit --no-fund
RUN npm run build

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS python-builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS final
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=python-builder /install /usr/local
COPY . .
# web/dist/ is produced by stage 1 — the FastAPI app looks here at boot
# (WEB_DIST_DIR default) and mounts every file under /assets + /.
COPY --from=web-builder /web/dist ./web/dist

RUN useradd --create-home --uid 10001 bot && chown -R bot:bot /app
USER bot

CMD ["python", "main.py"]
