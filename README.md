# Equality Bot — Discord Store Bot

Bot Discord untuk manajemen toko digital — dari katalog produk, sistem tiket pembelian, pembayaran, hingga invoice otomatis. Dibangun untuk server Discord yang menjual produk digital seperti skin, gamepass, nitro, dan sejenisnya.

---

## Fitur Utama

- **Katalog Produk** — Tampilkan produk berdasarkan kategori dengan tombol interaktif
- **Sistem Tiket** — Setiap pembelian membuka channel tiket pribadi antara buyer dan admin
- **Multi Metode Bayar** — QRIS, DANA, dan BCA
- **Invoice Otomatis** — Invoice dikirim ke log channel dan DM buyer setelah transaksi selesai
- **Giveaway** — Sistem giveaway dengan countdown, tombol join, dan auto-pilih pemenang
- **Auto React** — Reaksi emoji otomatis pada pesan di channel tertentu
- **Broadcast** — Kirim pengumuman ke semua member (cooldown 1x/hari)
- **Statistik** — Rekap transaksi harian dan total omset
- **Auto Backup** — Backup database otomatis setiap 6 jam ke channel Discord
- **Auto Restart** — Bot otomatis restart jika crash

---

## Instalasi

### Persyaratan
- Python 3.10+
- pip
- Git

### Langkah Instalasi

**1. Clone repo**
```bash
git clone https://github.com/EqualityDev/fishit-bot.git
cd fishit-bot
```

**2. Install dependencies**
```bash
pip install -r requirements.txt --break-system-packages
```

**3. Buat file `.env`**
```bash
cp .env.example .env
nano .env
```

**4. Jalankan bot**
```bash
bash start.sh
```

---

## Konfigurasi `.env`

| Variable | Wajib | Keterangan |
|---|---|---|
| `DISCORD_TOKEN` | Ya | Token bot dari Discord Developer Portal |
| `STORE_NAME` | Ya | Nama toko yang tampil di embed dan status bot |
| `STAFF_ROLE_NAME` | Ya | Nama role admin/staff di server (default: `Admin Store`) |
| `DANA_NUMBER` | Ya | Nomor DANA untuk pembayaran |
| `BCA_NUMBER` | Ya | Nomor rekening BCA untuk pembayaran |
| `LOG_CHANNEL_ID` | Ya | ID channel untuk log invoice |
| `WATCHDOG_WEBHOOK` | Tidak | Webhook Discord untuk notifikasi saat bot crash/restart |
| `STORE_THUMBNAIL` | Tidak | URL gambar thumbnail toko |
| `STORE_BANNER` | Tidak | URL banner utama toko |
| `BROADCAST_BANNER` | Tidak | URL banner untuk broadcast |
| `INVOICE_BANNER` | Tidak | URL banner untuk invoice |
| `WELCOME_BANNER` | Tidak | URL banner di tiket pembelian |

---

## Manajemen Produk

Produk bisa ditambahkan via command Discord atau import file `.xlsx`/`.csv`.

Format file import:

| id | name | price | category |
|---|---|---|---|
| 1 | Skin Rare | 50000 | LIMITED SKIN |
| 2 | Nitro 1 Bulan | 75000 | NITRO |

Kategori yang didukung: `LIMITED SKIN`, `GAMEPASS`, `CRATE`, `BOOST`, `NITRO`, `RED FINGER`, `MIDMAN`, `LAINNYA`

---

## Slash Commands

### Untuk Semua User

| Command | Keterangan |
|---|---|
| `/catalog` | Tampilkan katalog produk |
| `/qris` | Tampilkan QR code pembayaran |
| `/history` | Lihat riwayat transaksi pribadi |
| `/help` | Tampilkan daftar command |

### Giveaway

| Command | Keterangan |
|---|---|
| `/giveaway` | Mulai giveaway baru |
| `/giveaway_end` | Akhiri giveaway lebih awal |
| `/giveaway_reroll` | Reroll pemenang |
| `/giveaway_list` | Lihat giveaway yang sedang aktif |

### Admin

| Command | Keterangan |
|---|---|
| `/addproduct` | Tambah produk baru |
| `/editprice` | Edit harga produk |
| `/editname` | Edit nama produk |
| `/deleteitem` | Hapus produk |
| `/importproduk` | Import produk dari file xlsx/csv |
| `/setspotlight` | Tandai produk sebagai spotlight |
| `/unsetspotlight` | Hapus produk dari spotlight |
| `/listspotlight` | Lihat daftar produk spotlight |
| `/spotlight` | Kirim embed spotlight ke channel |
| `/uploadqris` | Upload QR code baru |
| `/broadcast` | Kirim pengumuman ke semua member |
| `/fakeinvoice` | Buat invoice dummy untuk testing |
| `/allhistory` | Lihat semua riwayat transaksi |
| `/stats` | Statistik transaksi |
| `/statdetail` | Statistik detail per periode |
| `/export` | Export semua transaksi ke file |
| `/blacklist` | Blacklist user |
| `/unblacklist` | Hapus user dari blacklist |
| `/setreact` | Aktifkan auto react untuk staff di channel |
| `/setreactall` | Aktifkan auto react untuk semua pesan di channel |
| `/reactlist` | Lihat channel yang aktif auto react |
| `/backup` | Backup database manual |
| `/listbackup` | Lihat daftar file backup |
| `/restore` | Restore database dari backup |
| `/transcript` | Generate transcript channel tiket |
| `/ping` | Cek status dan latency bot |
| `/reboot` | Restart bot |
| `/migrate` | Migrasi data antar server |
| `/cleanupstats` | Bersihkan data statistik lama |
| `/resetdb` | Reset database (berbahaya!) |

---

## Struktur Folder

```
fishit-bot/
├── bot.py              # Entry point utama
├── config.py           # Konfigurasi dari .env
├── database.py         # Semua operasi database SQLite
├── utils.py            # Fungsi utility (invoice, transcript, dll)
├── start.sh            # Script jalankan bot + auto-restart
├── products.json       # Data produk awal (import pertama kali)
├── .env                # Konfigurasi rahasia (jangan di-commit!)
├── cogs/
│   ├── admin.py        # Command admin
│   ├── store.py        # Katalog, produk, history
│   ├── ticket.py       # Sistem tiket pembelian
│   ├── giveaway.py     # Sistem giveaway
│   └── react.py        # Auto react
├── backups/            # File backup database
└── transcripts/        # File HTML transcript tiket
```

---

## Developer

Dibuat oleh **Equality** — untuk keperluan toko digital di Discord.

---

> Bot ini bersifat open source dan boleh dimodifikasi sesuai kebutuhan.
