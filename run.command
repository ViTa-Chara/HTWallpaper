#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/data"
LOG_FILE="$LOG_DIR/run.log"
mkdir -p "$LOG_DIR"

{
  echo "[$(date)] start"
} >> "$LOG_FILE"

# Check for uv (system or local)
UV="uv"
if ! command -v uv &>/dev/null; then
  LOCAL_UV="$ROOT_DIR/.uv/uv"
  if [ -x "$LOCAL_UV" ]; then
    UV="$LOCAL_UV"
  else
    echo "[ERROR] uv not found. Please run setup.command first." >&2
    exit 1
  fi
fi

{
  echo "[$(date)] uv=$UV"
} >> "$LOG_FILE"

# Run with uv run
"$UV" run --no-dev -m app.tray &
PID=$!

{
  echo "[$(date)] pid=$PID"
} >> "$LOG_FILE"
