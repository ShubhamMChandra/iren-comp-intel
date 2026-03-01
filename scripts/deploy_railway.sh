#!/usr/bin/env bash
# Deploy API or frontend to Railway.
# Usage: ./scripts/deploy_railway.sh [api|frontend]
# Default: api (if no arg).
#
# API:      railway up from repo root (imports config, database, etc. from parent)
# Frontend: railway up from frontend/ so Railpack detects Node, not Python

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SERVICE="${1:-api}"
if [[ "$SERVICE" != "api" && "$SERVICE" != "frontend" ]]; then
  echo "Usage: $0 [api|frontend]"
  exit 1
fi

echo "Running Railway pre-deploy checks..."
cd "$ROOT"
python3 -m pytest -m railway -q --tb=short
echo "Pre-deploy checks passed."

echo "Deploying $SERVICE to Railway..."
railway service "$SERVICE"

if [[ "$SERVICE" == "frontend" ]]; then
  cd "$ROOT/frontend"
else
  cd "$ROOT"
fi

railway up
echo "Done. Check Railway dashboard for build status."
