#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/data"
LOG_FILE="$LOG_DIR/run.log"
mkdir -p "$LOG_DIR"
{
  echo "[$(date)] start"
} >> "$LOG_FILE"

PY_EXEC="$ROOT_DIR/.venv/bin/python3"
if [ ! -x "$PY_EXEC" ]; then
  PY_EXEC="$ROOT_DIR/.venv/bin/python"
fi
if [ ! -x "$PY_EXEC" ]; then
  PY_EXEC="python3"
fi
{
  echo "[$(date)] python=$PY_EXEC"
} >> "$LOG_FILE"

"$PY_EXEC" -m app.tray &

PID=$!
{
  echo "[$(date)] pid=$PID"
} >> "$LOG_FILE"
