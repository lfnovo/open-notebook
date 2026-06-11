#!/usr/bin/env bash
# Cross-platform dev launcher (Linux/macOS). Delegates to dev.py.
#   ./dev.sh            bring everything up (combined logs, Ctrl+C stops all)
#   ./dev.sh --skip-sync
#   ./dev.sh stop       force-stop anything left running
set -euo pipefail
cd "$(dirname "$0")"
exec uv run python dev.py "$@"
