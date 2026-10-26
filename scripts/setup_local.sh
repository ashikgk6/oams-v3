#!/usr/bin/env bash
# Create venv and install OAMS dependencies (no Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
REQ="$ROOT/requirements.txt"

echo "==> OAMS local setup (no Docker)"
echo "    Root: $ROOT"

# Prefer system interpreters (avoid a stale activated .venv on PATH).
# Fall back to Bazel-managed CPython if system python3-venv/ensurepip is missing.
pick_python() {
  for candidate in /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import ensurepip' 2>/dev/null; then
      echo "$candidate"
      return
    fi
  done
  local bazel_py
  bazel_py="$(find /home/dell/.cache/bazel -path '*/bin/python3.11' 2>/dev/null | head -n 1 || true)"
  if [ -n "$bazel_py" ] && [ -x "$bazel_py" ]; then
    echo "$bazel_py"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then command -v python3; return; fi
  echo ""
}

PYTHON_BIN="$(pick_python)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: python3 not found. Install Python 3.10+."
  exit 1
fi

PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "==> Using $PYTHON_BIN ($PYTHON_VERSION)"

cd "$BACKEND"
rm -rf .venv

echo "==> Creating virtualenv at backend/.venv"
if ! "$PYTHON_BIN" -m venv .venv; then
  echo
  echo "ERROR: could not create venv (often missing python3-venv)."
  echo "On Debian/Ubuntu:  sudo apt install python3.10-venv python3-pip"
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! python -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip missing inside venv."
  echo "On Debian/Ubuntu:  sudo apt install python3.10-venv python3-pip"
  exit 1
fi

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing requirements from $REQ"
pip install -r "$REQ"

if [ ! -f .env ]; then
  if [ -f "$ROOT/.env.local.example" ]; then
    cp "$ROOT/.env.local.example" .env
    echo "==> Created backend/.env from .env.local.example"
  fi
else
  echo "==> backend/.env already exists (left unchanged)"
fi

echo
echo "Setup complete."
echo "Start:  ./scripts/run_local.sh"
echo "Open:   http://localhost:8000"
echo "Login:  admin@office.local / admin123"
