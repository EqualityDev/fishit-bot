# 🛒 CELLYN STORE Discord Bot

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Discord](https://img.shields.io/badge/discord-py-blue.svg)](https://discordpy.readthedocs.io/)

Bot Discord untuk toko jual Robux dengan sistem tiket, database permanen, dan backup otomatis.

## 📋 Fitur

- ✅ Katalog produk
- ✅ Sistem tiket
- ✅ Database SQLite
- ✅ Backup otomatis setiap 6 jam
- ✅ Export transaksi ke CSV
- ✅ Blacklist user
- ✅ Statistik penjualan
- ✅ HTML transcript tiket

## 🚀 Cara Install

```bash
# Clone repo
git clone https://github.com/EqualityDev/fishit-bot.git
cd fishit-bot

# Install dependencies
pip install -r requirements.txt

# Setup .env
cp .env.example .env
nano .env  # isi token dll

# Jalankan
python bot.py

⚙️ Konfigurasi

File .env:

env
DISCORD_TOKEN=your_token
LOG_CHANNEL_ID=your_channel_id
DANA_NUMBER=123456789
BCA_NUMBER=123456
RATE=
STAFF_ROLE_NAME=🔰 Admin Store
```

 License

 MIT © EqualityDev

 ```
