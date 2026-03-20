#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/primopositum/Workspace/Python/GestionalePresenzeTrasferte/AppPresenze"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
MANAGE_PY="$PROJECT_DIR/manage.py"

LOG_DIR="/home/primopositum/Workspace/Python/GestionalePresenzeTrasferte/log"
LOG_FILE="$LOG_DIR/django_auto_timeentry.log"

# --- Log rotation settings ---
MAX_BYTES=$((5 * 1024 * 1024))  # 5 MB
KEEP=10                        # keep last 10 rotated logs (older are deleted)

export TZ="Europe/Rome"

mkdir -p "$LOG_DIR"

rotate_logs_if_needed() {
  [[ -f "$LOG_FILE" ]] || return 0

  local size
  size=$(stat -c%s "$LOG_FILE" 2>/dev/null || wc -c < "$LOG_FILE")

  if (( size < MAX_BYTES )); then
    return 0
  fi

  # Rotate to: django_auto_timeentry.log.YYYYmmdd_HHMMSS
  local ts rotated
  ts=$(date '+%Y%m%d_%H%M%S')
  rotated="${LOG_FILE}.${ts}"

  mv "$LOG_FILE" "$rotated"
  : > "$LOG_FILE"

  # Cleanup old rotated logs, keep newest $KEEP
  local base
  base="$(basename "$LOG_FILE")"

  # Newest first, delete from item KEEP+1 onwards
  ls -1t "$LOG_DIR" \
    | grep -E "^${base}\.[0-9]{8}_[0-9]{6}$" \
    | tail -n +"$((KEEP + 1))" \
    | while read -r f; do
        rm -f "$LOG_DIR/$f"
      done
}

rotate_logs_if_needed

{
  echo "===== START $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
  echo "User: $(whoami)"
  echo "Project dir: $PROJECT_DIR"
} >> "$LOG_FILE"

cd "$PROJECT_DIR" || {
  echo "ERRORE: impossibile entrare in $PROJECT_DIR" >> "$LOG_FILE"
  exit 1
}

"$PYTHON_BIN" "$MANAGE_PY" genera_timeentries_settimana >> "$LOG_FILE" 2>&1

echo "===== END   $(date '+%Y-%m-%d %H:%M:%S %Z') =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

