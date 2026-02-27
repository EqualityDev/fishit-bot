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

BOT_SCRIPT="bot.py"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$BOT_DIR/watchdog.log"
MAX_RETRIES=3
CHECK_INTERVAL=30

# Load .env
if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs)
fi

STORE_NAME_ENV=$(grep -E "^STORE_NAME=" "$BOT_DIR/.env" 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'")
if [ -z "$STORE_NAME_ENV" ]; then
    STORE_NAME_ENV="Store"
fi

WEBHOOK_URL="$WATCHDOG_WEBHOOK"

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
echo -e "${WHITE}      Watchdog Monitor  │  ${CYAN}${STORE_NAME_ENV}${WHITE}  │  Built by Equality${NC}"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -z "$WEBHOOK_URL" ]; then
    echo -e "${RED}  ✗ ERROR: WATCHDOG_WEBHOOK tidak ditemukan di .env!${NC}"
    exit 1
fi

log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case "$level" in
        INFO)    echo -e "${CYAN}  [${timestamp}] ℹ  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        OK)      echo -e "${GREEN}  [${timestamp}] ✓  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        WARN)    echo -e "${YELLOW}  [${timestamp}] ⚠  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        ERROR)   echo -e "${RED}  [${timestamp}] ✗  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        *)       echo -e "${GRAY}  [${timestamp}] •  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
    esac
}

send_embed() {
    local title="$1"
    local description="$2"
    local color="$3"
    local extra_fields="$4"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"embeds\": [{
                \"title\": \"$title\",
                \"description\": \"$description\",
                \"color\": $color,
                \"fields\": $extra_fields,
                \"footer\": {\"text\": \"EQUALITY BOT • Watchdog\"},
                \"timestamp\": \"$timestamp\"
            }]
        }" > /dev/null
}

get_uptime() {
    local pid=$1
    if [ -n "$pid" ]; then
        ps -o etimes= -p "$pid" 2>/dev/null | awk '{
            s=$1
            h=int(s/3600); m=int((s%3600)/60); s=s%60
            printf "%d jam %d menit %d detik", h, m, s
        }'
    else
        echo "tidak diketahui"
    fi
}

start_bot() {
    cd "$BOT_DIR"
    python3 bot.py >> "$LOG_FILE" 2>&1 &
    echo $!
}

echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log INFO "Watchdog dimulai — interval: ${CHECK_INTERVAL}s, max retry: ${MAX_RETRIES}x"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

send_embed \
    "🟢 WATCHDOG AKTIF" \
    "Watchdog mulai memantau bot." \
    "3066993" \
    "[{\"name\": \"Interval\", \"value\": \"${CHECK_INTERVAL} detik\", \"inline\": true}, {\"name\": \"Max Retry\", \"value\": \"${MAX_RETRIES}x\", \"inline\": true}]"

BOT_PID=$(pgrep -f "$BOT_SCRIPT" | head -1)
BOT_START_TIME=$(date +%s)
retries=0

while true; do
    sleep $CHECK_INTERVAL

    BOT_PID=$(pgrep -f "$BOT_SCRIPT" | head -1)

    if [ -n "$BOT_PID" ]; then
        retries=0
        log OK "Bot hidup (PID: $BOT_PID)"
    else
        DOWN_TIME=$(date '+%H:%M:%S')
        UPTIME=$(( $(date +%s) - BOT_START_TIME ))
        H=$((UPTIME/3600)); M=$(((UPTIME%3600)/60)); S=$((UPTIME%60))
        UPTIME_STR="${H} jam ${M} menit ${S} detik"

        log ERROR "Bot MATI! Uptime terakhir: $UPTIME_STR"

        send_embed \
            "🔴 BOT MATI" \
            "Bot tidak merespon, sedang direstart..." \
            "15158332" \
            "[{\"name\": \"Waktu Mati\", \"value\": \"$DOWN_TIME\", \"inline\": true}, {\"name\": \"Uptime Terakhir\", \"value\": \"$UPTIME_STR\", \"inline\": true}, {\"name\": \"Percobaan Restart\", \"value\": \"$((retries+1))/${MAX_RETRIES}\", \"inline\": true}]"

        retries=$((retries + 1))

        if [ $retries -le $MAX_RETRIES ]; then
            log WARN "Restart percobaan $retries/$MAX_RETRIES..."
            BOT_PID=$(start_bot)
            BOT_START_TIME=$(date +%s)
            sleep 5

            if kill -0 "$BOT_PID" 2>/dev/null; then
                log OK "Bot berhasil direstart (PID: $BOT_PID)"
                send_embed \
                    "✅ BOT BERHASIL DIRESTART" \
                    "Bot kembali online!" \
                    "3066993" \
                    "[{\"name\": \"PID Baru\", \"value\": \"$BOT_PID\", \"inline\": true}, {\"name\": \"Percobaan\", \"value\": \"$retries/${MAX_RETRIES}\", \"inline\": true}]"
                retries=0
            else
                log ERROR "Restart gagal!"
            fi
        else
            log ERROR "Max retry tercapai! Butuh intervensi manual."
            send_embed \
                "❌ RESTART GAGAL" \
                "Bot sudah dicoba restart ${MAX_RETRIES}x tapi tetap mati.\n**Butuh intervensi manual!**" \
                "15158332" \
                "[{\"name\": \"Max Retry\", \"value\": \"${MAX_RETRIES}x sudah dicoba\", \"inline\": true}, {\"name\": \"Action\", \"value\": \"Cek Termux sekarang!\", \"inline\": true}]"
            retries=0
        fi
    fi
done
