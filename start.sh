#!/bin/bash

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m'

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$BOT_DIR/watchdog.log"
MAX_RETRIES=5
MANUAL_STOP=0

# Load .env
if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs 2>/dev/null)
fi

STORE_NAME_ENV=$(grep -E "^STORE_NAME=" "$BOT_DIR/.env" 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'")
[ -z "$STORE_NAME_ENV" ] && STORE_NAME_ENV="Store"
WEBHOOK_URL="${WATCHDOG_WEBHOOK:-}"

# Tangkap Ctrl+C — tandai sebagai manual stop
trap 'MANUAL_STOP=1; echo -e "\n${YELLOW}  ⚠  Dihentikan manual.${NC}"; exit 0' SIGINT SIGTERM

log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case "$level" in
        INFO)  echo -e "${CYAN}  [${timestamp}] ℹ  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        OK)    echo -e "${GREEN}  [${timestamp}] ✓  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        WARN)  echo -e "${YELLOW}  [${timestamp}] ⚠  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        ERROR) echo -e "${RED}  [${timestamp}] ✗  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
    esac
}

send_webhook() {
    [ -z "$WEBHOOK_URL" ] && return
    local title="$1" desc="$2" color="$3" fields="$4"
    local ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"embeds\":[{\"title\":\"$title\",\"description\":\"$desc\",\"color\":$color,\"fields\":$fields,\"footer\":{\"text\":\"EQUALITY BOT • Monitor\"},\"timestamp\":\"$ts\"}]}" \
        > /dev/null 2>&1
}

show_banner() {
    clear
    echo -e "${CYAN}"
    echo "  ███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗     ██╗████████╗██╗   ██╗"
    echo "  ██╔════╝██╔═══██╗██║   ██║██╔══██╗██║     ██║╚══██╔══╝╚██╗ ██╔╝"
    echo "  █████╗  ██║   ██║██║   ██║███████║██║     ██║   ██║    ╚████╔╝ "
    echo "  ██╔══╝  ██║▄▄ ██║██║   ██║██╔══██║██║     ██║   ██║     ╚██╔╝  "
    echo "  ███████╗╚██████╔╝╚██████╔╝██║  ██║███████╗██║   ██║      ██║   "
    echo "  ╚══════╝ ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝      ╚═╝  "
    echo -e "${NC}"
    echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}      Discord Store Bot  │  ${CYAN}${STORE_NAME_ENV}${WHITE}  │  Built by Equality${NC}"
    echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_update() {
    git fetch origin main --quiet 2>/dev/null
    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse origin/main 2>/dev/null)

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo -e "${YELLOW}  ⚠  UPDATE TERSEDIA!${NC}"
        echo ""
        echo -e "${GRAY}  📋 Changelog:${NC}"
        git log HEAD..origin/main --oneline --no-merges 2>/dev/null | sed 's/^/     /'
        echo ""
        echo -e "${WHITE}  Update sekarang? (y/n): ${NC}\c"
        read -r jawaban
        if [ "$jawaban" = "y" ] || [ "$jawaban" = "Y" ]; then
            echo -e "${CYAN}  📥 Mengunduh update...${NC}"
            git pull origin main
            echo -e "${GREEN}  ✓ Update selesai!${NC}"
        else
            echo -e "${GRAY}  ⏭  Melewati update...${NC}"
        fi
    else
        echo -e "${GREEN}  ✓ Bot sudah versi terbaru!${NC}"
    fi
    echo ""
}

trim_log() {
    if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 1000 ]; then
        tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
}

# ── MAIN ──────────────────────────────────────────────────────────

show_banner
check_update

echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log INFO "Auto-restart aktif — max retry: ${MAX_RETRIES}x"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

send_webhook "🟢 BOT STARTING" "Bot sedang dijalankan." "3066993" \
    "[{\"name\":\"Store\",\"value\":\"${STORE_NAME_ENV}\",\"inline\":true}]"

retries=0

while true; do
    cd "$BOT_DIR"
    log INFO "Menjalankan bot... (percobaan ke-$((retries+1)))"

    python3 bot.py
    EXIT_CODE=$?

    # Kalau MANUAL_STOP=1 berarti Ctrl+C sudah ditangkap trap
    [ $MANUAL_STOP -eq 1 ] && break

    trim_log

    retries=$((retries + 1))
    log ERROR "Bot mati! (exit: $EXIT_CODE) — Percobaan $retries/$MAX_RETRIES"

    send_webhook "🔴 BOT MATI" "Bot crash, mencoba restart..." "15158332" \
        "[{\"name\":\"Exit Code\",\"value\":\"$EXIT_CODE\",\"inline\":true},{\"name\":\"Percobaan\",\"value\":\"$retries/${MAX_RETRIES}\",\"inline\":true}]"

    if [ $retries -ge $MAX_RETRIES ]; then
        log ERROR "Max retry tercapai! Butuh intervensi manual."
        send_webhook "❌ RESTART GAGAL" "Bot sudah dicoba restart ${MAX_RETRIES}x.\n**Cek Termux sekarang!**" "15158332" \
            "[{\"name\":\"Action\",\"value\":\"Manual restart diperlukan\",\"inline\":true}]"
        break
    fi

    log WARN "Restart dalam 10 detik..."
    sleep 10

    log OK "Restart ke-$retries..."
    send_webhook "🔄 RESTART" "Bot sedang direstart." "16776960" \
        "[{\"name\":\"Percobaan\",\"value\":\"$retries/${MAX_RETRIES}\",\"inline\":true}]"
done
