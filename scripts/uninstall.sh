#!/bin/bash
set -e

# Liftoff install location. Override with:
#   LIFTOFF_APP="/path/to/Liftoff.app" ./scripts/uninstall.sh
LIFTOFF_APP="${LIFTOFF_APP:-$HOME/Library/Application Support/Steam/steamapps/common/Liftoff/Liftoff.app}"
LIFTOFF_PLUGINS="$LIFTOFF_APP/Contents/PlugIns"
LIFTOFF_MANAGED="$LIFTOFF_APP/Contents/Resources/Data/Managed"

ORIG_BUNDLE="$LIFTOFF_PLUGINS/Rewired_MacOS_orig.bundle"
TARGET_BUNDLE="$LIFTOFF_PLUGINS/Rewired_MacOS.bundle"
if [ -f "$LIFTOFF_MANAGED/Rewired_Core_orig.dll" ]; then
    mv "$LIFTOFF_MANAGED/Rewired_Core_orig.dll" "$LIFTOFF_MANAGED/Rewired_Core.dll"
fi
if [ -f "$LIFTOFF_MANAGED/Rewired_OSX_orig.dll" ]; then
    mv "$LIFTOFF_MANAGED/Rewired_OSX_orig.dll" "$LIFTOFF_MANAGED/Rewired_OSX.dll"
fi

if [ -f "$ORIG_BUNDLE" ]; then
    cp "$ORIG_BUNDLE" "$TARGET_BUNDLE"
    install_name_tool -id "@rpath/Rewired_MacOS.bundle" "$TARGET_BUNDLE" 2>/dev/null || true
    codesign --force --sign - "$TARGET_BUNDLE"
    rm -f "$ORIG_BUNDLE"
    echo "✅ Berhasil mengembalikan Rewired_MacOS.bundle original di Liftoff.app."
else
    echo "ℹ️ Backup Rewired_MacOS_orig.bundle tidak ditemukan (Liftoff sudah menggunakan file original)."
fi
