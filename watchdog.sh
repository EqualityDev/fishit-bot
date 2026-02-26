#!/bin/bash

# ==============================
#   EQUALITY BOT - WATCHDOG
# ==============================

BOT_SCRIPT="bot.py"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$BOT_DIR/watchdog.log"
MAX_RETRIES=3
CHECK_INTERVAL=30

# Load .env
if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs)
fi

WEBHOOK_URL="$WATCHDOG_WEBHOOK"

if [ -z "$WEBHOOK_URL" ]; then
    echo "[WATCHDOG] ERROR: WATCHDOG_WEBHOOK tidak ditemukan di .env!"
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
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

log "Watchdog dimulai. Monitoring setiap ${CHECK_INTERVAL}s..."
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
        log "Bot hidup (PID: $BOT_PID)"
    else
        DOWN_TIME=$(date '+%H:%M:%S')
        UPTIME=$(( $(date +%s) - BOT_START_TIME ))
        H=$((UPTIME/3600)); M=$(((UPTIME%3600)/60)); S=$((UPTIME%60))
        UPTIME_STR="${H} jam ${M} menit ${S} detik"

        log "Bot MATI! Uptime terakhir: $UPTIME_STR"

        send_embed \
            "🔴 BOT MATI" \
            "Bot tidak merespon, sedang direstart..." \
            "15158332" \
            "[{\"name\": \"Waktu Mati\", \"value\": \"$DOWN_TIME\", \"inline\": true}, {\"name\": \"Uptime Terakhir\", \"value\": \"$UPTIME_STR\", \"inline\": true}, {\"name\": \"Percobaan Restart\", \"value\": \"$((retries+1))/${MAX_RETRIES}\", \"inline\": true}]"

        retries=$((retries + 1))

        if [ $retries -le $MAX_RETRIES ]; then
            log "Restart percobaan $retries/$MAX_RETRIES..."
            BOT_PID=$(start_bot)
            BOT_START_TIME=$(date +%s)
            sleep 5

            if kill -0 "$BOT_PID" 2>/dev/null; then
                log "Bot berhasil direstart (PID: $BOT_PID)"
                send_embed \
                    "✅ BOT BERHASIL DIRESTART" \
                    "Bot kembali online!" \
                    "3066993" \
                    "[{\"name\": \"PID Baru\", \"value\": \"$BOT_PID\", \"inline\": true}, {\"name\": \"Percobaan\", \"value\": \"$retries/${MAX_RETRIES}\", \"inline\": true}]"
                retries=0
            else
                log "Restart gagal!"
            fi
        else
            log "Max retry tercapai! Butuh intervensi manual."
            send_embed \
                "❌ RESTART GAGAL" \
                "Bot sudah dicoba restart ${MAX_RETRIES}x tapi tetap mati.\n**Butuh intervensi manual!**" \
                "15158332" \
                "[{\"name\": \"Max Retry\", \"value\": \"${MAX_RETRIES}x sudah dicoba\", \"inline\": true}, {\"name\": \"Action\", \"value\": \"Cek Termux sekarang!\", \"inline\": true}]"
            retries=0
        fi
    fi
done
