# External Directory Architecture

The External User Directory feature allows SupportBot to connect to a secondary, external MongoDB database (owned by the operator) to dynamically resolve user metadata and subscription statuses (VIP status, tier labels, custom display badges) without requiring explicit API integration or synchronization.

## Data Flow

1.  **Configuration (Wizard):**
    Admins configure the external directory connection via an interactive chat wizard (`/admin` -> External Directory). They provide a connection URI, target database, and collection, along with mapping rules indicating how documents identify Telegram users and how fields relate to the canonical `ResolvedUserSignal` object. The MongoDB connection URI is encrypted via AES-256 and stored using `cryptography.fernet` to keep raw credentials out of the config document.

2.  **Resolution (Provider & Cache):**
    The `ExternalDirectoryProvider` instances the database connection. When a user creates or replies to a ticket, or when an admin fetches data, the bot resolves the `DirectoryProviderLike` protocol via the DI `Container`. The provider checks an in-memory LRU cache with a 5-minute TTL. If missing, it fetches the user document and parses the raw data into a `ResolvedUserSignal` using the `Interpreter`.

3.  **Application (Interpreter):**
    The `Interpreter` maps external fields according to the configured rule kinds:
    -   `Boolean`: e.g. `{"premium": true}` maps to `is_vip: True`.
    -   `Enum`: e.g. `{"plan": "gold"}` maps to `is_vip: True`, `tier_label: "Gold"`, `tier_rank_order: 3`.
    -   `Numeric Threshold`: e.g. `{"ltv": 5000}` triggers `is_vip: True` if the value exceeds a threshold, otherwise returning a calculated scalar priority score.

4.  **UI & Engine Integration (Surfacing):**
    The canonical `ResolvedUserSignal` seamlessly integrates with:
    -   **Rules Engine**: Rule conditions evaluating `user.is_vip` or `user.tier_label` will natively apply.
    -   **Ticket Headers**: Chat views (like `ticket_header` and `agent_inbox`) display custom emojis or text badges dynamically per user.
    -   **Mini-App**: React SPA endpoints optionally retrieve `is_vip` flags alongside display badges, rendering them safely inside the frontend UI natively.