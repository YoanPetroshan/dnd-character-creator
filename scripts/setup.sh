#!/usr/bin/env bash
# One-time setup: Python venv + dependencies, frontend dependencies + build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
.venv/bin/pip install -r server/requirements.txt
(cd frontend && npm ci && npm run build)
echo "done. Start with scripts/start.sh" >&2
