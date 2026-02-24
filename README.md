# 🛒 Cellyn Store Bot

> A fully-featured Discord store bot for digital product sales — built with Python, discord.py, and SQLite.

---

## ✨ Features

### 🧾 Transaction System
- Interactive ticket-based order flow
- Payment method selection: **QRIS**, **DANA**, **BCA**
- Auto-generated invoice numbers (daily reset, format `INV-YYYYMMDD-0001`)
- Invoice sent to customer via **DM** + logged to **#log-transaksi**
- HTML transcript saved on ticket close
- Payment proof upload before confirming PAID

### 📦 Product Catalog
- Dynamic catalog with category buttons
- Spotlight system — pin up to 5 featured products
- Quantity adjustment (+/-) inside ticket
- Live cache with auto-refresh

### 🔐 Admin Tools
- `/addproduct`, `/editprice`, `/editname`, `/deleteitem`
- `/blacklist` / `/unblacklist` user management
- `/broadcast` with preview before sending
- `/stats`, `/statdetail`, `/allhistory`, `/export` (CSV)
- `/backup`, `/listbackup`, `/restore` — manual DB management
- `/resetdb`, `/cleanupstats` with modal confirmation

### ⚙️ Automation
- **Auto Backup** — runs on bot start + every 6 hours, sent to `#backup-db`
- **Auto Daily Summary** — sent every midnight to `#backup-db` with total transactions, revenue, and payment breakdown
- **Backup Retention** — keeps only the last 5 local backups
- **Member Count** — voice channel auto-updated every 10 minutes

### 🎯 Auto React
- `/setreact` — auto-react to staff messages in specific channels
- `/setreactall` — auto-react to all messages in specific channels
- 3-second cooldown per channel to prevent rate limiting

### 🔒 Safety & Reliability
- SQLite with **WAL mode** — no database locked errors under concurrent load
- `active_tickets` re-hydrated from DB on bot restart — no lost ticket data
- DB as **single source of truth** for products — no overwrite on restart
- Invoice counter stored in DB — safe from file corruption
- `!cancel` restricted to ticket owner or staff only

---

## 🗂️ Project Structure

```
cellyn-store-bot/
├── bot.py              # Entry point, shared state, background tasks
├── config.py           # Constants and environment variables
├── database.py         # SimpleDB class + ProductsCache
├── utils.py            # Helper functions
├── products.json       # Initial product list (first-run import only)
├── .env                # Secret config (not committed)
├── .env.example        # Environment variable template
├── setup.sh            # One-time install script
├── import_products.py  # Excel/CSV product importer
└── cogs/
    ├── react.py        # Auto-react system
    ├── admin.py        # Admin commands
    ├── store.py        # Store commands and catalog
    └── ticket.py       # Ticket system and interaction handlers
```

---

## 🚀 Installation (Termux / Linux)

### Requirements
- Python 3.10+
- Termux (Android) or any Linux environment
- A Discord Bot Token

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/EqualityDev/fishit-bot.git
cd fishit-bot

# 2. Run the setup script
bash setup.sh

# 3. Fill in your .env file
nano .env

# 4. Start the bot
python3 bot.py
```

### `.env` Configuration

```env
DISCORD_TOKEN=your_bot_token_here
DANA_NUMBER=08xxxxxxxxxx
BCA_NUMBER=1234567890
RATE=85
STAFF_ROLE_NAME=Admin Store
BUYER_ROLE_NAME=Royal Customer
LOG_CHANNEL_ID=
STORE_THUMBNAIL=https://your-thumbnail-url.png
STORE_BANNER=https://your-banner-url.png
INVOICE_BANNER=https://your-invoice-banner-url.png
BROADCAST_BANNER=https://your-broadcast-banner-url.png
```

---

## 📥 Importing Products via Excel

You can bulk-import products using an Excel or CSV file.

### 1. Prepare your Excel file

| id | name | price | category |
|----|------|-------|----------|
| 1 | Nitro 1 Month | 75000 | NITRO |
| 2 | Nitro 3 Month | 200000 | NITRO |
| 3 | Robux 1000 | 85000 | ROBUX |

### 2. Export as CSV
In Excel: `File → Save As → CSV (Comma delimited)`

### 3. Run the importer

```bash
python3 import_products.py products_data.csv
```

### 4. Restart the bot
```bash
python3 bot.py
```

Products will be imported to the database and appear in `/catalog` immediately.

> **Note:** If the database already has products, the importer will **merge** — existing IDs are updated, new IDs are added. No data is lost.

---

## 💬 Commands

### Customer Commands
| Command | Description |
|---------|-------------|
| `/catalog` | Browse all products by category |
| `/rate` | Check current Robux rate |
| `/history` | View your own transaction history |
| `/items` | View items in your active ticket |
| `/additem` | Add item to active ticket |
| `/removeitem` | Remove item from active ticket |
| `/qris` | View QRIS payment QR code |
| `!cancel` | Cancel your active ticket |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/addproduct` | Add a new product |
| `/editprice` | Edit product price |
| `/editname` | Edit product name |
| `/deleteitem` | Delete a product |
| `/listitems` | List all products (sent via DM) |
| `/setrate` | Update Robux rate |
| `/uploadqris` | Upload QRIS image |
| `/setspotlight` | Pin a product to spotlight (max 5) |
| `/unsetspotlight` | Remove product from spotlight |
| `/listspotlight` | View all spotlight products |
| `/stats` | View sales statistics |
| `/statdetail` | View detailed statistics |
| `/allhistory` | View all transactions for a user |
| `/export` | Export transaction data as CSV |
| `/broadcast` | Send message to all members (with preview) |
| `/blacklist` | Blacklist a user |
| `/unblacklist` | Remove user from blacklist |
| `/backup` | Manual database backup |
| `/listbackup` | List available backups |
| `/restore` | Restore a backup |
| `/resetdb` | Reset database (requires confirmation) |
| `/cleanupstats` | Clean up old statistics |
| `/fakeinvoice` | Generate a test invoice |
| `/setreact` | Set auto-react for staff messages |
| `/setreactall` | Set auto-react for all messages |
| `/reactlist` | View auto-react configuration |
| `/ping` | Check bot status |
| `/reboot` | Restart the bot |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Discord Library | discord.py 2.x |
| Database | SQLite (WAL mode) |
| Async DB | aiosqlite |
| Config | python-dotenv |
| Deployment | Termux (Android) |

---

## 📊 Database Schema

```sql
transactions   — invoice, user_id, items, total_price, payment_method, timestamp
products       — id, name, price, category, spotlight
blacklist      — user_id, reason, timestamp
active_tickets — channel_id, user_id, items, total_price, payment_method, status, created_at
auto_react     — channel_id, emojis (staff only)
auto_react_all — channel_id, emojis (all users)
settings       — key, value (invoice counter, qris_url, etc.)
```

---

## 📝 License

This project is private and proprietary.
All rights reserved © 2026 **Cellyn Store**

---

## 👤 Credits

**Developed by:** EqualityDev  
**Store:** Cellyn Store  
**Discord:** [Join our server](https://discord.gg/yourlink)

---

*Built with ❤️ for Cellyn Store*
