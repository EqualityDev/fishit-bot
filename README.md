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
- Anti-spam ticket — 1 active ticket per user, redirects to existing ticket

### 📦 Product Catalog
- Dynamic catalog with category buttons
- Spotlight system — pin up to 5 featured products
- Quantity adjustment (+/-) inside ticket
- Import products via Excel/CSV directly from Discord (`/importproduk`)
- Harga item Robux mengikuti rate pasar saat ini

### 🔐 Admin Tools
- `/addproduct`, `/editprice`, `/editname`, `/deleteitem`
- `/importproduk` — bulk import products from `.xlsx` or `.csv` file
- `/blacklist` / `/unblacklist` user management
- `/broadcast` with preview before sending + log to `#backup-db`
- `/stats`, `/statdetail`, `/allhistory`, `/export` (CSV)
- `/backup`, `/listbackup`, `/restore` — manual DB management
- `/resetdb`, `/cleanupstats` with modal confirmation

### 🎉 Giveaway System
- `/giveaway` — start giveaway with duration (10m, 2h, 1d) and winner count
- React 🎉 to join
- `/giveaway_end` — end early
- `/giveaway_reroll` — reroll winner
- `/giveaway_list` — view active giveaways

### ⚙️ Automation
- **Auto Backup** — runs on bot start + every 6 hours, sent to `#backup-db`
- **Auto Daily Summary** — sent every midnight to `#backup-db`
- **Error Logging** — all errors automatically sent to `#backup-db`
- **Backup Retention** — keeps only the last 5 local backups
- **Member Count** — voice channel auto-updated every 10 minutes (excludes bots)

### 🎯 Auto React
- `/setreact` — auto-react to staff messages
- `/setreactall` — auto-react to all messages
- 3-second cooldown per channel, max 10 emoji

### 🔒 Safety & Reliability
- SQLite with **WAL mode** — no database locked errors
- `active_tickets` re-hydrated from DB on bot restart
- DB as **single source of truth** for products
- Invoice counter stored in DB — safe from file corruption

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
├── import_products.py  # CLI product importer (Excel/CSV)
└── cogs/
    ├── react.py        # Auto-react system
    ├── admin.py        # Admin commands
    ├── store.py        # Store commands and catalog
    ├── ticket.py       # Ticket system
    └── giveaway.py     # Giveaway system
```

---

## 🚀 Installation (Termux / Linux)

### Quick Setup

```bash
git clone https://github.com/EqualityDev/fishit-bot.git
cd fishit-bot
bash setup.sh
nano .env
python3 bot.py
```

### `.env` Configuration

```env
DISCORD_TOKEN=your_bot_token_here
DANA_NUMBER=08xxxxxxxxxx
BCA_NUMBER=1234567890
STAFF_ROLE_NAME=Admin Store
BUYER_ROLE_NAME=Royal Customer
LOG_CHANNEL_ID=
STORE_THUMBNAIL=https://your-thumbnail-url.png
STORE_BANNER=https://your-catalog-banner-url.png
INVOICE_BANNER=https://your-terimakasih-banner-url.png
BROADCAST_BANNER=https://your-broadcast-banner-url.png
WELCOME_BANNER=https://your-welcome-banner-url.png
```

> Semua variabel banner bersifat opsional — jika tidak diisi, bot menggunakan banner default Cellyn Store.

---

## 📥 Importing Products

### Via Discord (Recommended)
1. Download template: `template_produk_cellyn.xlsx`
2. Fill in your products
3. In Discord: `/importproduk` → upload file
4. Done — catalog updates instantly

### Via CLI (Termux)
```bash
python3 import_products.py products.csv
```

### Template Format

| id | name | price | category |
|----|------|-------|----------|
| 1 | Nitro 1 Month | 75000 | NITRO |
| 2 | Robux 1000 | 85000 | ROBUX |

---

## 💬 Commands

### Customer Commands
| Command | Description |
|---------|-------------|
| `/catalog` | Browse all products |
| `/history` | View transaction history |
| `/items` | View items in active ticket |
| `/additem` | Add item to ticket |
| `/removeitem` | Remove item from ticket |
| `/qris` | View QRIS QR code |
| `!cancel` | Cancel active ticket |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/addproduct` | Add a new product |
| `/editprice` | Edit product price |
| `/editname` | Edit product name |
| `/deleteitem` | Delete a product |
| `/listitems` | List all products |
| `/importproduk` | Import products from Excel/CSV |
| `/uploadqris` | Upload QRIS image |
| `/setspotlight` | Pin product to spotlight (max 5) |
| `/unsetspotlight` | Remove from spotlight |
| `/listspotlight` | View spotlight products |
| `/stats` | Sales statistics |
| `/statdetail` | Detailed statistics |
| `/allhistory` | All transactions for a user |
| `/export` | Export data as CSV |
| `/broadcast` | Send message to all members |
| `/blacklist` | Blacklist a user |
| `/unblacklist` | Remove from blacklist |
| `/backup` | Manual database backup |
| `/listbackup` | List available backups |
| `/restore` | Restore a backup |
| `/resetdb` | Reset database |
| `/cleanupstats` | Clean up statistics |
| `/fakeinvoice` | Generate test invoice |
| `/giveaway` | Start a giveaway |
| `/giveaway_end` | End giveaway early |
| `/giveaway_reroll` | Reroll winner |
| `/giveaway_list` | View active giveaways |
| `/setreact` | Set auto-react (staff) |
| `/setreactall` | Set auto-react (all) |
| `/reactlist` | View auto-react config |
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
| Excel Import | openpyxl |
| Config | python-dotenv |
| Deployment | Railway / Termux (Android) |

---

## 📝 License

This project is private and proprietary.  
All rights reserved © 2026 **Cellyn Store**

---

## 👤 Credits

**Developed by:** EqualityDev  
**Store:** Cellyn Store  

*Built with ❤️ for Cellyn Store*
