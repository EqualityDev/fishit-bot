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
 ```

MIT License

Copyright (c) 2026 EqualityDev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.