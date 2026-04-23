# Thin wrapper: Railway / Heroku / Nixpacks builders that auto-detect
# the repo-root Dockerfile get the same image as
# ``deploy/docker/Dockerfile``. Keep this file in sync with that one —
# or, for local builds, use ``docker build -f deploy/docker/Dockerfile .``
# directly.
#
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 bot && chown -R bot:bot /app
USER bot

CMD ["python", "main.py"]
