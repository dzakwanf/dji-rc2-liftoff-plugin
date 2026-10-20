#!/bin/bash
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

export DYLD_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:${DYLD_LIBRARY_PATH}"

# Prefer the project venv; fall back to the system python3 + pyusb.
if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3 || true)"
    if [ -z "$PYTHON" ]; then
        echo "Error: python3 tidak ditemukan. Install via 'brew install python3'." >&2
        exit 1
    fi
fi

exec "$PYTHON" "$ROOT/src/dji_rc2_liftoff.py" "$@"
