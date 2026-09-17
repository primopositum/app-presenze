#!/usr/bin/env sh
set -eu
export TZ="${TZ:-Europe/Rome}"
STAMP_FILE="${SCHEDULER_STAMP_FILE:-/tmp/genera_timeentries_settimana.last_run}"
CHECK_INTERVAL_SECONDS="${SCHEDULER_CHECK_INTERVAL_SECONDS:-30}"
HC_URL="${SCHEDULER_HC_URL:-}"

# Healthchecks è opzionale. Usiamo la libreria standard perché python:3.12-slim
# non include wget/curl; un ping fallito viene riportato nei log ma non blocca il job.
ping_hc() {
  if [ -n "$HC_URL" ]; then
    if ! python -c "import sys; from urllib.request import urlopen; response = urlopen(sys.argv[1], timeout=10); response.close()" "${HC_URL}$1"; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] healthcheck ping failed: ${HC_URL}$1" >&2
    fi
  fi
}

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
    ping_hc "/start"

    if python manage.py genera_timeentries_settimana; then
      echo "$today" > "$STAMP_FILE"
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run completed"
      # Ping di successo
      ping_hc ""
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run failed"
      # Ping di fallimento
      ping_hc "/fail"
    fi
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
