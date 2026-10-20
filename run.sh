#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:${DYLD_LIBRARY_PATH}"
exec "$HERE/.venv/bin/python" "$HERE/dji_rc2_liftoff.py" "$@"
