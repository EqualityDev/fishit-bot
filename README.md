# 🤖 STORE DISCORD BOT

Bot Discord untuk toko jual beli Robux dengan sistem tiket, database permanen, dan manajemen produk.

## ✨ **FITUR UTAMA**

### 🛒 **Sistem Penjualan**
- ✅ **Katalog Produk Dinamis** - Menampilkan produk dari file `products.json` dengan kategori otomatis
- ✅ **Tombol per Kategori** - Tombol "BUY [Kategori]" untuk memulai pembelian
- ✅ **Rate Robux** - Bisa diatur dan ditampilkan dengan command `/rate`
- ✅ **Invoice Otomatis** - Notifikasi transaksi di channel log

### 🎫 **Sistem Tiket & Order**
- ✅ **Tiket Private** - Channel khusus untuk setiap transaksi
- ✅ **Manajemen Item** - Tombol ➕/➖ untuk menambah/mengurangi jumlah item
- ✅ **Pilihan Pembayaran** - User bisa pilih metode (QRIS/DANA/BCA)
- ✅ **Konfirmasi Staff** - Tombol **PAID** untuk staff mengonfirmasi pembayaran
- ✅ **Permanent Ticket Storage** - Data tiket tersimpan di database SQLite, **tidak hilang** walau bot restart
- ✅ **Auto-Close** - Channel tiket otomatis dihapus 5 detik setelah dikonfirmasi

### 📊 **Database & Data Permanen**
- ✅ **SQLite Database** - Semua transaksi, produk, blacklist, dan tiket aktif tersimpan permanen
- ✅ **Backup Otomatis** - Backup database setiap 6 jam ke folder `backups/`
- ✅ **Backup Manual** - Command `/backup` untuk backup instan
- ✅ **Export CSV** - Export data transaksi ke file CSV dengan filter user/hari
- ✅ **HTML Transcript** - Riwayat percakapan tiket tersimpan dalam format HTML (mirip Discord asli)

### 👥 **Manajemen User**
- ✅ **History Transaksi** - User bisa cek riwayat belanja sendiri dengan `/history`
- ✅ **All History (Admin)** - Lihat SEMUA transaksi user dengan `/allhistory`
- ✅ **Blacklist System** - Blokir user nakal (command `/blacklist`, `/unblacklist`, `/listblacklist`)
- ✅ **Auto-Role** - Role "Royal Customer" otomatis diberikan setelah transaksi pertama

### 📈 **Statistik & Laporan**
- ✅ **Statistik Penjualan** - Lihat total transaksi dan omset hari ini, 7 hari, 30 hari (`/stats`)
- ✅ **List Backup** - Lihat daftar file backup yang tersedia (`/listbackup`)
- ✅ **Reset Database (Admin)** - Hapus semua data transaksi (`/resetdb`)

### 🛠️ **Fitur Admin**
- ✅ **Manajemen Produk** - Tambah, edit harga, edit nama, hapus produk via command
- ✅ **List Items** - Lihat semua item yang tersedia (`/listitems`)
- ✅ **Set Rate** - Ubah rate Robux (`/setrate`)
- ✅ **QRIS Upload** - Upload gambar QR code (`/uploadqris`) dan lihat QR code (`/qris`)
- ✅ **Fake Invoice** - Buat invoice palsu untuk testing/social proof (`/fakeinvoice`)
- ✅ **Refresh Catalog** - Refresh tampilan katalog (`/refreshcatalog`)
- ✅ **Auto React** - Setting auto-react di channel tertentu (`/setreact`, `/reactlist`)

### 🧰 **Fitur Tambahan**
- ✅ **Ping Command** - Cek respon bot (`/ping`)
- ✅ **Help Command** - Bantuan penggunaan bot (`/help`)
- ✅ **Broadcast** - Kirim pesan ke semua channel (jika diaktifkan)
- ✅ **Error Handling** - Penanganan error yang informatif

## 📋 **DAFTAR COMMAND**

### 👤 **User Commands**
| Command | Deskripsi |
|---------|-----------|
| `/catalog` | Lihat semua produk yang tersedia |
| `/rate` | Cek rate Robux saat ini |
| `/history` | Lihat riwayat transaksi pribadi |
| `/help` | Tampilkan bantuan |
| `/ping` | Cek respon bot |

### 🛡️ **Admin Commands**
| Command | Deskripsi |
|---------|-----------|
| `/stats` | Lihat statistik penjualan |
| `/allhistory [user]` | Lihat semua transaksi user |
| `/blacklist <user> [reason]` | Blacklist user |
| `/unblacklist <user>` | Hapus user dari blacklist |
| `/listblacklist` | Lihat daftar blacklist |
| `/addproduct` | Tambah produk baru |
| `/editprice <id> <harga>` | Edit harga produk |
| `/editname <id> <nama>` | Edit nama produk |
| `/deleteitem <id>` | Hapus produk |
| `/listitems` | Lihat semua item |
| `/setrate <rate>` | Ubah rate Robux |
| `/uploadqris` | Upload QR code |
| `/qris` | Lihat QR code |
| `/fakeinvoice <item_id> [qty] [metode]` | Buat invoice palsu |
| `/refreshcatalog` | Refresh tampilan katalog |
| `/backup` | Backup database manual |
| `/listbackup` | Lihat daftar backup |
| `/export [filter_user] [filter_days]` | Export data ke CSV |
| `/resetdb` | Reset database (hapus semua transaksi) |
| `/setreact [emoji1] [emoji2] ...` | Setting auto-react di channel |
| `/reactlist` | Lihat channel auto-react aktif |

## 🚀 **CARA INSTALL**

### Prerequisites
- Python 3.8+
- Git
- Discord Bot Token ([Ambil di sini](https://discord.com/developers/applications))

### Langkah Instalasi

1. **Clone repository**
   ```bash
   git clone https://github.com/EqualityDev/fishit-bot.git
   cd fishit-bot
   ```

2. **Buat virtual environment (opsional)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   nano .env  # atau edit dengan editor teks
   ```
   
   Isi file `.env`:
   ```env
   DISCORD_TOKEN=token_bot_kamu_disini
   LOG_CHANNEL_ID=id_channel_log
   DANA_NUMBER=1234567893
   BCA_NUMBER=1234567
   RATE=85
   STAFF_ROLE_NAME=Admin Store
   BUYER_ROLE_NAME=Royal Customer
   ```

5. **Jalankan bot**
   ```bash
   python bot.py
   ```

## 📦 **DEPLOY KE RAILWAY**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=)

1. Push repository ke GitHub
2. Login ke [Railway](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Add environment variables (isi sesuai `.env`)
5. Deploy otomatis

## 📁 **STRUKTUR FILE**
```
fishit-bot/
├── bot.py                 # File utama bot
├── products.json          # Daftar produk
├── store.db               # Database SQLite
├── .env                   # Environment variables
├── .env.example           # Template env
├── requirements.txt       # Dependencies
├── README.md              # Dokumentasi ini
├── backups/               # Folder backup otomatis
├── transcripts/           # Folder HTML transcript
└── broadcast_cooldown.json # Data cooldown broadcast
```

## ⚙️ **KONFIGURASI PRODUK**

Edit file `products.json` untuk menambah/mengubah produk:

```json
[
  {
    "id": 1,
    "name": "80 Robux",
    "price": 15000,
    "category": "RUX"
  },
  {
    "id": 2,
    "name": "160 Robux",
    "price": 30000,
    "category": "ROBUX"
  }
]
```

## 👨‍💻 **TENTANG DEVELOPER**

**EqualityDev** adalah pengembang dan pemilik Bot. dikembangkan secara mandiri untuk memudahkan transaksi dan memberikan pengalaman belanja terbaik bagi member.

### 📞 **Kontak**
- Discord: `equalitystar`
- GitHub: [@EqualityDev](https://github.com/EqualityDev)

### ⭐ **Dukungan**
Jika kamu suka dengan bot ini, silakan beri star di repository!