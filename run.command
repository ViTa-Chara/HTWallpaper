#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/data"
LOG_FILE="$LOG_DIR/run.log"
STATE_FILE="$LOG_DIR/env_state.json"
mkdir -p "$LOG_DIR"

log() {
  echo "[$(date)] $1" >> "$LOG_FILE"
}

find_python() {
  for c in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      "$c" -c 'import sys; exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 && { echo "$c"; return 0; }
    fi
  done
  return 1
}

venv_py="$ROOT_DIR/.venv/bin/python"
if [ ! -x "$venv_py" ]; then
  venv_py="$ROOT_DIR/.venv/bin/python3"
fi

first_launch=0
[ ! -f "$STATE_FILE" ] && first_launch=1

check_venv() {
  local py="$1"
  [ -x "$py" ] || return 1
  "$py" -c 'import fastapi,uvicorn,apscheduler,psutil,pystray;from PIL import Image' >/dev/null 2>&1
}

if ! check_venv "$venv_py"; then
  log "bootstrap: create or repair venv"
  rm -rf "$ROOT_DIR/.venv"

  py_cmd="$(find_python || true)"
  if [ -z "$py_cmd" ]; then
    echo "Python 3.10+ not found. Please install Python and retry." >&2
    exit 1
  fi

  "$py_cmd" -m venv "$ROOT_DIR/.venv"
  venv_py="$ROOT_DIR/.venv/bin/python"
  [ -x "$venv_py" ] || venv_py="$ROOT_DIR/.venv/bin/python3"

  "$venv_py" -m pip install --disable-pip-version-check -U pip
  "$venv_py" -m pip install --disable-pip-version-check -r "$ROOT_DIR/requirements.txt"

  check_venv "$venv_py" || { echo "Dependency check failed after install." >&2; exit 1; }
  log "bootstrap ok using $py_cmd"
fi

cat > "$STATE_FILE" <<JSON
{"status":"ready","python":"$venv_py","updatedAt":"$(date +%FT%T)"}
JSON

log "python=$venv_py"
"$venv_py" -m app.tray &
PID=$!
log "pid=$PID"
