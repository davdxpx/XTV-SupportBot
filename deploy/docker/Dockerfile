# syntax=docker/dockerfile:1.7
# Multi-stage build for XTV-SupportBot.
#
# Stage 1 — build the React SPA (only when web/ exists).
# Stage 2 — install Python deps + the package.
# Final  — slim runtime with the SPA assets baked into /web/.

# ---------------------------------------------------------------------------
FROM node:25-slim AS web-builder
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

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY main.py ./

RUN pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS final
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=python-builder /install /usr/local
COPY --from=python-builder /app/src /app/src
COPY --from=python-builder /app/main.py /app/main.py
# Match the path the FastAPI app looks for at boot
# (settings.WEB_DIST_DIR default = "web/dist" relative to /app).
COPY --from=web-builder /web/dist /app/web/dist

RUN useradd --create-home --uid 10001 bot && chown -R bot:bot /app
USER bot

# health-check hint — the bot exposes /health via FastAPI when
# API_ENABLED=true; the Telegram worker answers fine without it.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "main.py"]
