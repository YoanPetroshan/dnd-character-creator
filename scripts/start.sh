#!/usr/bin/env bash
# Production-style start: waitress serves the Flask app (API + built frontend) on one origin.
# Usage: scripts/start.sh [--rebuild]      env: HOST (127.0.0.1), PORT (8000), THREADS (4)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -x "$ROOT/.venv/bin/waitress-serve" ]; then
  echo "error: $ROOT/.venv is missing or lacks waitress. Run scripts/setup.sh first." >&2
  exit 1
fi

REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    *) echo "error: unknown argument: $arg (only --rebuild is supported)" >&2; exit 2 ;;
  esac
done

if [ "$REBUILD" = "1" ] || [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "building the frontend..." >&2
  (cd "$ROOT/frontend" && npm ci && npm run build)
fi

cd "$ROOT/server"
exec ../.venv/bin/waitress-serve --listen="${HOST:-127.0.0.1}:${PORT:-8000}" --threads="${THREADS:-4}" app:app
