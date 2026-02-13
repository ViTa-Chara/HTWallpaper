#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CFG="$ROOT_DIR/.venv/pyvenv.cfg"

if [ ! -f "$CFG" ]; then
  echo "[ERROR] 未找到 .venv/pyvenv.cfg，请先创建虚拟环境。"
  exit 1
fi

VERSION_LINE="$(awk -F '=' '/^[[:space:]]*version[[:space:]]*=/{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit}' "$CFG" || true)"
TARGET_MM=""
if [ -n "$VERSION_LINE" ]; then
  TARGET_MM="$(printf '%s' "$VERSION_LINE" | awk -F. '{print $1"."$2}')"
fi

CANDIDATES=()
if [ -n "$TARGET_MM" ]; then
  CANDIDATES+=("python$TARGET_MM")
fi
CANDIDATES+=("python3" "python")

PY_EXEC=""
for cand in "${CANDIDATES[@]}"; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; exit(0 if sys.executable else 1)' >/dev/null 2>&1; then
      PY_EXEC="$($cand -c 'import sys; print(sys.executable)')"
      break
    fi
  fi
done

if [ -z "$PY_EXEC" ]; then
  echo "[ERROR] 没有找到可用的 Python，可先安装 Python 3。"
  exit 1
fi

PY_HOME="$(dirname "$PY_EXEC")"

"$PY_EXEC" - "$CFG" "$PY_HOME" <<'PY'
from pathlib import Path
import sys
cfg = Path(sys.argv[1])
home = sys.argv[2]
lines = cfg.read_text(encoding='utf-8').splitlines()
updated = False
for i, line in enumerate(lines):
    if line.strip().startswith('home ='):
        lines[i] = f'home = {home}'
        updated = True
        break
if not updated:
    lines.insert(0, f'home = {home}')
cfg.write_text("\n".join(lines) + "\n", encoding='utf-8')
PY

echo "[OK] pyvenv.cfg 已更新: home = $PY_HOME"
