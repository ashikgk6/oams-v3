#!/usr/bin/env bash
# Run OAMS API locally (no Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"

if [ ! -d "$BACKEND/.venv" ]; then
  echo "Virtualenv missing. Run ./scripts/setup_local.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source "$BACKEND/.venv/bin/activate"
cd "$BACKEND"

# Load backend/.env if present (simple KEY=VALUE lines)
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "Starting OAMS on http://0.0.0.0:8000 ..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
