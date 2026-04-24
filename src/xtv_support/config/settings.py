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
    # Directory pyrofork writes the ``*.session`` file to. Default is
    # the current working directory, which on Railway/Render/Fly/Heroku
    # is ephemeral — every deploy wipes the session and forces a fresh
    # ``auth.ImportBotAuthorization`` call, which triggers Telegram's
    # aggressive ``FLOOD_WAIT_X`` rate limit on rapid redeploys. Mount
    # a persistent volume and point this at it (e.g. ``/data``) to keep
    # the session across deploys and avoid the re-auth entirely.
    SESSION_DIR: str = "."

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

    # --- Branding ---
    # Customisable branding so every deploy can call itself whatever it
    # wants. Every UI card that used to hardcode "XTV Support" now pulls
    # from here. All optional — if empty, the defaults kick in.
    BRAND_NAME: str = "Support"
    BRAND_TAGLINE: str = "We're here to help."
    # URL-like branding buttons shown on the onboarding card. Leave empty
    # to hide. Telegram deep-links (``https://t.me/…``) render as
    # tappable buttons; anything else is treated as a regular URL.
    BRAND_MAIN_CHANNEL_URL: str = ""
    BRAND_MAIN_CHANNEL_LABEL: str = "Main channel"
    BRAND_SUPPORT_CHANNEL_URL: str = ""
    BRAND_SUPPORT_CHANNEL_LABEL: str = "Updates"
    BRAND_BACKUP_CHANNEL_URL: str = ""
    BRAND_BACKUP_CHANNEL_LABEL: str = "Backup"

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

    # --- Admin SPA ---
    # When ``WEB_ENABLED=true`` and ``web/dist/`` exists, the FastAPI app
    # mounts the React admin SPA at ``/`` with an ``index.html`` fallback
    # so React-Router paths survive a refresh. Set to ``false`` to serve
    # only the API (e.g. if you expose the SPA via a separate service).
    WEB_ENABLED: bool = True
    # Relative path (from repo root) to the built SPA. Only used when the
    # default ``web/dist`` layout doesn't apply — e.g. a custom build in CI.
    WEB_DIST_DIR: str = "web/dist"

    # --- Dual-mode UI (Chat vs Telegram WebApp) ---
    # ``chat`` (default) renders classic inline-keyboard buttons; ``webapp``
    # replaces every panel with a single Open-App tile that launches the
    # bundled SPA as a Telegram Mini-App; ``hybrid`` keeps both so the user
    # can pick per tap.
    UI_MODE: str = "chat"
    # Public HTTPS URL of the Mini-App — must be served over TLS and must
    # match the bot's WebApp domain configured via @BotFather.
    WEBAPP_URL: str = ""
    # When true, the bot calls ``setChatMenuButton`` at boot so every user
    # sees a persistent "Open App" button next to the message composer.
    WEBAPP_SET_MENU_BUTTON: bool = False
    WEBAPP_MENU_BUTTON_TEXT: str = "Open App"

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
    def ui_mode(self):
        """Parsed :class:`~xtv_support.core.ui_mode.UIMode` (tolerant).

        Kept as a method so the import stays lazy — the ``ui_mode``
        module doesn't need pydantic loaded to import cleanly in tests.
        """
        from xtv_support.core.ui_mode import UIMode

        return UIMode.parse(self.UI_MODE)

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
