from __future__ import annotations

import os

# Provide the minimal env required by pydantic-settings so app.config imports
# cleanly in tests. The values are fake but syntactically valid.
os.environ.setdefault("API_ID", "1")
os.environ.setdefault("API_HASH", "x")
os.environ.setdefault("BOT_TOKEN", "1:x")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("ADMIN_CHANNEL_ID", "-1001234567890")
os.environ.setdefault("ADMIN_IDS", "1,2,3")
os.environ.setdefault("LOG_LEVEL", "WARNING")
