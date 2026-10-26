#!/usr/bin/env bash
# Prefer: python -m app.worker  (idempotent via job_runs)
set -euo pipefail
BASE_URL="${OAMS_URL:-http://localhost:8000}"
SECRET="${INTERNAL_CRON_SECRET:-change-me-cron-secret}"
curl -fsS -X POST "${BASE_URL}/api/internal/finalize-day" \
  -H "X-Cron-Secret: ${SECRET}"
echo
