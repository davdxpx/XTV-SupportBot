from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram ---
    API_ID: int
    API_HASH: SecretStr
    BOT_TOKEN: SecretStr

    # --- Mongo ---
    MONGO_URI: SecretStr
    MONGO_DB_NAME: str = "xtvfeedback_bot"

    # --- Roles ---
    # Keep as raw str so pydantic-settings does not try to JSON-decode a
    # single id like "1" into an int. We split it in the validator below.
    ADMIN_IDS_RAW: str = Field(default="", alias="ADMIN_IDS")
    ADMIN_CHANNEL_ID: int

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    DEBUG_MODE: bool = False

    # --- SLA ---
    SLA_WARN_MINUTES: int = 30
    SLA_BREACH_MINUTES: int = 120

    # --- Auto close ---
    AUTO_CLOSE_DAYS: int = 7
    AUTO_CLOSE_SWEEP_MINUTES: int = 10

    # --- Anti-spam ---
    COOLDOWN_RATE: int = 10
    COOLDOWN_WINDOW: int = 60
    COOLDOWN_MUTE_SECONDS: int = 300

    # --- Broadcast ---
    BROADCAST_CONCURRENCY: int = 20
    BROADCAST_FLOOD_BUFFER_MS: int = 250

    # --- UI ---
    PROGRESS_EDIT_INTERVAL: float = 1.5

    # --- Topic creation ---
    TOPIC_CREATE_RETRY: int = 3

    # --- Audit / error logging ---
    ERROR_LOG_TOPIC_ID: int | None = None
    AUDIT_RETENTION_DAYS: int = 90

    # --- Localization ---
    DEFAULT_LANG: str = "en"

    # --- REST API (FastAPI) ---
    # When ``API_ENABLED=true`` the boot sequence starts uvicorn alongside
    # the Telegram client. On Railway / Render / Fly, ``PORT`` is injected
    # by the platform and takes precedence over ``API_PORT``.
    API_ENABLED: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    # Railway/Heroku style port override. Kept separate so users can force
    # a specific port locally while still deferring to ``$PORT`` in prod.
    PORT: int | None = None
    # Comma-separated list of allowed origins for CORS. Use ``*`` to allow
    # everything (fine for read-only keys, risky for write endpoints).
    API_CORS_ORIGINS: str = ""
    API_RATE_LIMIT_PER_MINUTE: int = 120

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def effective_api_port(self) -> int:
        """Return the port the API should bind to.

        ``$PORT`` (set automatically by Railway, Render, Heroku, Fly) wins
        over ``API_PORT`` so the same image works on any PaaS without
        custom config.
        """
        return int(self.PORT) if self.PORT else int(self.API_PORT)

    @property
    def cors_origins(self) -> list[str]:
        raw = (self.API_CORS_ORIGINS or "").strip()
        if not raw:
            return []
        return [p.strip() for p in raw.split(",") if p.strip()]

    @property
    def ADMIN_IDS(self) -> list[int]:
        raw = (self.ADMIN_IDS_RAW or "").strip()
        if not raw:
            return []
        out: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except ValueError:
                continue
        return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
