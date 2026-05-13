#!/usr/bin/env sh
set -eu
export TZ="${TZ:-Europe/Rome}"
STAMP_FILE="${SCHEDULER_STAMP_FILE:-/tmp/genera_timeentries_settimana.last_run}"
CHECK_INTERVAL_SECONDS="${SCHEDULER_CHECK_INTERVAL_SECONDS:-30}"
HC_URL="https://hc-ping.com/dc3849ac-cf7e-40a8-add6-7dc156754644"

echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] scheduler started (TZ=$TZ)"
echo "Stamp file: $STAMP_FILE"

while true; do
  set -- $(date '+%u %H:%M %F')
  dow="$1"     # 1..7 (Mon..Sun)
  hhmm="$2"    # HH:MM
  today="$3"   # YYYY-MM-DD

  last_run=""
  if [ -f "$STAMP_FILE" ]; then
    last_run="$(cat "$STAMP_FILE" 2>/dev/null || true)"
  fi

  if [ "$dow" = "1" ] && [ "$hhmm" = "00:00" ] && [ "$last_run" != "$today" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] running genera_timeentries_settimana"

    # Ping di start
    wget -q --spider "${HC_URL}/start" || true

    if python manage.py genera_timeentries_settimana; then
      echo "$today" > "$STAMP_FILE"
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run completed"
      # Ping di successo
      wget -q --spider "${HC_URL}" || true
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run failed"
      # Ping di fallimento
      wget -q --spider "${HC_URL}/fail" || true
    fi
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
