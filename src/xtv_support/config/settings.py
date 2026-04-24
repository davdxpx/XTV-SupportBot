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

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

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
