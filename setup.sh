#!/bin/bash

echo "=============================="
echo "  CELLYN STORE BOT - SETUP"
echo "=============================="
echo ""

# Install Python packages
echo "📦 Installing dependencies..."
pip install discord.py python-dotenv aiosqlite --break-system-packages

# Install openpyxl untuk Excel importer (optional)
pip install openpyxl --break-system-packages 2>/dev/null

# Buat folder yang dibutuhkan
echo "📁 Creating required folders..."
mkdir -p backups transcripts

# Copy .env.example jika .env belum ada
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  File .env telah dibuat dari .env.example"
    echo "    Silakan isi token dan konfigurasi di file .env"
    echo "    Gunakan: nano .env"
else
    echo "✅ File .env sudah ada, dilewati."
fi

echo ""
echo "=============================="
echo "  SETUP SELESAI!"
echo "=============================="
echo ""
echo "Langkah selanjutnya:"
echo "  1. nano .env          → isi konfigurasi"
echo "  2. python3 bot.py     → jalankan bot"
echo ""
