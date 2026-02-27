#!/bin/bash

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m'

# Load STORE_NAME from .env
STORE_NAME=$(grep -E "^STORE_NAME=" .env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'")
if [ -z "$STORE_NAME" ]; then
    STORE_NAME="Store"
fi

clear

echo -e "${CYAN}"
echo "  ███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗     ██╗████████╗██╗   ██╗"
echo "  ██╔════╝██╔═══██╗██║   ██║██╔══██╗██║     ██║╚══██╔══╝╚██╗ ██╔╝"
echo "  █████╗  ██║   ██║██║   ██║███████║██║     ██║   ██║    ╚████╔╝ "
echo "  ██╔══╝  ██║▄▄ ██║██║   ██║██╔══██║██║     ██║   ██║     ╚██╔╝  "
echo "  ███████╗╚██████╔╝╚██████╔╝██║  ██║███████╗██║   ██║      ██║   "
echo "  ╚══════╝ ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝      ╚═╝   "
echo -e "${NC}"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${WHITE}      Discord Store Bot  │  ${CYAN}${STORE_NAME}${WHITE}  │  Built by Equality${NC}"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Cek koneksi git
git fetch origin main --quiet 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo -e "${YELLOW}  ⚠  UPDATE TERSEDIA!${NC}"
    echo ""
    echo -e "${GRAY}  📋 Changelog:${NC}"
    git log HEAD..origin/main --oneline --no-merges | sed 's/^/     /'
    echo ""
    echo -e "${WHITE}  Update sekarang? (y/n)${NC} "
    read -r jawaban

    if [ "$jawaban" = "y" ] || [ "$jawaban" = "Y" ]; then
        echo ""
        echo -e "${CYAN}  📥 Mengunduh update...${NC}"
        git pull origin main
        echo -e "${GREEN}  ✓ Update selesai!${NC}"
        echo ""
    else
        echo ""
        echo -e "${GRAY}  ⏭  Melewati update, menjalankan versi lama...${NC}"
        echo ""
    fi
else
    echo -e "${GREEN}  ✓ Bot sudah versi terbaru!${NC}"
    echo ""
fi

echo -e "${CYAN}  ▶ Menjalankan BOT...${NC}"
echo ""
python3 bot.py
