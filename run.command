#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT_DIR/data"
LOG_FILE="$LOG_DIR/run.log"
mkdir -p "$LOG_DIR"
{
  echo "[$(date)] start"
} >> "$LOG_FILE"

INIT_MARKER="$LOG_DIR/init.ok"

if [ ! -x "$ROOT_DIR/.venv/bin/python3" ] && [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  {
    echo "[$(date)] .venv missing, bootstrap"
  } >> "$LOG_FILE"

  PY_CMD="python3"
  if ! command -v "$PY_CMD" >/dev/null 2>&1; then
    PY_CMD="python"
  fi
  if ! command -v "$PY_CMD" >/dev/null 2>&1; then
    echo "Python not found. Please install Python 3.10+ and retry." >&2
    exit 1
  fi

  "$PY_CMD" -m venv "$ROOT_DIR/.venv"
  VENV_PY="$ROOT_DIR/.venv/bin/python"
  "$VENV_PY" -m pip install -U pip
  "$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"
  {
    echo "[$(date)] init ok using $PY_CMD"
  } > "$INIT_MARKER"
fi

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
