#!/bin/bash

echo "=============================="
echo "  EQUALITY BOT - STARTUP"
echo "=============================="
echo ""

# Cek koneksi git
git fetch origin main --quiet 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "⚠️  UPDATE TERSEDIA!"
    echo ""
    echo "📋 Changelog:"
    git log HEAD..origin/main --oneline --no-merges
    echo ""
    echo "Apakah kamu ingin update sekarang? (y/n)"
    read -r jawaban

    if [ "$jawaban" = "y" ] || [ "$jawaban" = "Y" ]; then
        echo ""
        echo "📥 Mengunduh update..."
        git pull origin main
        echo "✅ Update selesai!"
        echo ""
    else
        echo ""
        echo "⏭️  Melewati update, menjalankan versi lama..."
        echo ""
    fi
else
    echo "✅ Bot sudah versi terbaru!"
    echo ""
fi

echo "🚀 Menjalankan bot..."
python3 bot.py
