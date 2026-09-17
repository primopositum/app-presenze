#!/usr/bin/env sh
set -eu
export TZ="${TZ:-Europe/Rome}"
STAMP_FILE="${CONTRACT_ALERT_STAMP_FILE:-/tmp/email_contract_alert.last_run}"
RUN_AT="${CONTRACT_ALERT_TIME:-08:00}"
CHECK_INTERVAL_SECONDS="${SCHEDULER_CHECK_INTERVAL_SECONDS:-30}"
HC_URL="${CONTRACT_ALERT_HC_URL:-}"

# Ping healthchecks opzionale (python: l'immagine slim non ha wget/curl)
ping_hc() {
  if [ -n "$HC_URL" ]; then
    python -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=10)" "${HC_URL}$1" || true
  fi
}

echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] email_contract_alert scheduler started (TZ=$TZ, ogni giorno alle $RUN_AT)"
echo "Stamp file: $STAMP_FILE"

while true; do
  set -- $(date '+%H:%M %F')
  hhmm="$1"    # HH:MM
  today="$2"   # YYYY-MM-DD

  last_run=""
  if [ -f "$STAMP_FILE" ]; then
    last_run="$(cat "$STAMP_FILE" 2>/dev/null || true)"
  fi

  if [ "$hhmm" = "$RUN_AT" ] && [ "$last_run" != "$today" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] running email_contract_alert"
    # Stamp scritto prima dell'esecuzione: le email non vanno reinviate con un retry nello stesso giorno
    echo "$today" > "$STAMP_FILE"
    ping_hc "/start"

    if python manage.py email_contract_alert; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run completed"
      ping_hc ""
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run failed"
      ping_hc "/fail"
    fi
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
