# External User Directory

SupportBot can connect dynamically to your product's user database (MongoDB). This allows SupportBot to detect VIPs and prioritize them based on custom flags, subscriptions, tiers, or numeric scores found in your external database, without any manual data synchronization required.

## One-time Encryption Setup
Because SupportBot accesses your MongoDB, you first need to configure an encryption key in `.env` to ensure your external connection string is encrypted at rest within SupportBot's internal database.

```bash
# In your .env file
EXTERNAL_DB_SECRET_KEY=your-secure-32-byte-hex-string
```
See `SETUP.md` for generating this key.

## Guided Interactive Wizard
The setup process for the External User Directory is completely driven through SupportBot's Telegram chat. To begin:

1. Send `/admin` in your DM with SupportBot.
2. Open **External Directory** and tap **Start Setup**.

### 1. Connection Strings & Databases
The wizard first asks you for a MongoDB connection string. SupportBot encrypts it immediately after you send it and then asks you for the Database name and Collection name.

### 2. Testing the Connection
SupportBot will securely attempt to connect to the external database. If the connection fails (e.g. wrong password, unreachable network), the wizard will gracefully pause and give you the opportunity to correct the configuration.

### 3. Telegram ID and Expiration Selection
If the connection is successful, SupportBot fetches a sample user document and presents you with a list of top-level fields found in your database.
- You select the field representing the user's `Telegram ID`.
- You optionally select a field representing the user's expiration date or timestamp.

### 4. Field Interpretation Loop
This is the core mapping logic. For any other field in your document, you can configure exactly how SupportBot interprets it:

- **Boolean Field:** True/False fields. You decide whether `True` or `False` means "VIP" and tell SupportBot to map this to an internal concept like `vip_status` or `display_badge`.
- **Enum Field:** Categorical tiers (e.g., `free`, `pro`, `enterprise`). SupportBot queries your distinct values and asks you to rank them in order, optionally picking which rank serves as the minimum threshold to become VIP.
- **Numeric Field:** Score thresholds. SupportBot queries your min/max limits and asks for a cutoff limit.

You can configure as many fields as needed.

### 5. Review & Finalize
SupportBot shows a summary of everything configured. Once approved, it persists the settings and enables hot-reload on the provider. You can immediately click a button to test the mapping against your own Telegram ID right inside the chat.

## Fictional Worked Example
Imagine you own a web app `MyCoolApp` using a `subscribers` MongoDB collection.
- You send: `mongodb+srv://admin:pass@cluster.mongodb.net/`
- Database: `mycoolapp`
- Collection: `subscribers`

**Fields mapping:**
- Telegram ID field: `tg_id` (Type: string)
- Expiry field: `sub_expires_at` (Type: timestamp)
- Tier logic: `subscription.plan` (Enum).
    - The wizard shows: `free`, `pro`, `enterprise`.
    - You rank them: 1. `free`, 2. `pro`, 3. `enterprise`.
    - VIP threshold: `pro` and up.

**Result:** Any user messaging SupportBot who exists in the `mycoolapp.subscribers` collection, whose `sub_expires_at` is in the future, and has `subscription.plan` = `pro` or `enterprise` is instantly flagged as VIP, routed appropriately, and displayed distinctly to your agents in the dashboard.
