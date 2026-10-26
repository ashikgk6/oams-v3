#!/usr/bin/env bash
# Structural final check (no third-party imports required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
fail=0

check() {
  if [ -e "$1" ]; then
    echo "OK  $1"
  else
    echo "MISS $1"
    fail=1
  fi
}

echo "==> Checking required files"
check "$ROOT/requirements.txt"
check "$ROOT/SETUP_LOCAL.md"
check "$ROOT/README.md"
check "$BACKEND/app/main.py"
check "$BACKEND/app/container.py"
check "$BACKEND/app/worker.py"
check "$BACKEND/app/static/index.html"
check "$BACKEND/app/static/display.html"
check "$BACKEND/alembic/versions/0001_initial.py"
check "$BACKEND/tests/test_attendance_policy.py"

echo
echo "==> Python syntax check"
python3 - <<PY
import ast, pathlib, sys
root = pathlib.Path("$BACKEND")
errs = []
for p in root.rglob("*.py"):
    if ".venv" in p.parts:
        continue
    try:
        ast.parse(p.read_text())
    except SyntaxError as e:
        errs.append(f"{p}: {e}")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print(f"OK  parsed {len(list(root.rglob('*.py')))} python files")
PY

echo
if [ "$fail" -eq 0 ]; then
  echo "Structural check passed."
else
  echo "Structural check FAILED."
  exit 1
fi
