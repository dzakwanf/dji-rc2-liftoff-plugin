#!/bin/bash
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
LIFTOFF_PLUGINS="/Users/fis/Library/Application Support/Steam/steamapps/common/Liftoff/Liftoff.app/Contents/PlugIns"
ORIG_BUNDLE="$LIFTOFF_PLUGINS/Rewired_MacOS_orig.bundle"
TARGET_BUNDLE="$LIFTOFF_PLUGINS/Rewired_MacOS.bundle"

if [ ! -d "$LIFTOFF_PLUGINS" ]; then
    echo "Error: Folder Liftoff PlugIns tidak ditemukan di: $LIFTOFF_PLUGINS"
    exit 1
fi

mkdir -p "$HERE/build"

# 1. Backup original Rewired_MacOS.bundle jika belum ada backup
if [ ! -f "$ORIG_BUNDLE" ]; then
    echo "Membuat backup original Rewired_MacOS.bundle -> Rewired_MacOS_orig.bundle..."
    cp "$TARGET_BUNDLE" "$ORIG_BUNDLE"
fi

# 2. Set install_name pada Rewired_MacOS_orig.bundle & daftar simbol re-export
cp "$ORIG_BUNDLE" "$HERE/build/Rewired_MacOS_orig.bundle"
install_name_tool -id "@loader_path/Rewired_MacOS_orig.bundle" "$HERE/build/Rewired_MacOS_orig.bundle" 2>/dev/null || true
codesign --force --sign - "$HERE/build/Rewired_MacOS_orig.bundle"

nm -gU "$HERE/build/Rewired_MacOS_orig.bundle" | awk '{print $3}' | grep -E '^_RW|^_SetLogCallback' > "$HERE/build/reexport.txt"

# 3. Compile Universal (arm64 + x86_64) Rewired_MacOS.bundle proxy
echo "Mengompilasi plugin Universal (arm64 + x86_64) DJI RC 2 untuk Liftoff..."
clang -dynamiclib -arch arm64 -arch x86_64 -O2 \
  -DCALIB_FILE_PATH="\"$HERE/calib.json\"" \
  -framework Foundation -framework GameController \
  "$HERE/src/rewired_dji_rc2.m" \
  "$HERE/build/Rewired_MacOS_orig.bundle" \
  -Wl,-reexported_symbols_list,"$HERE/build/reexport.txt" \
  -install_name "@rpath/Rewired_MacOS.bundle" \
  -o "$HERE/build/Rewired_MacOS.bundle"

codesign --force --sign - "$HERE/build/Rewired_MacOS.bundle"

# 4. Pasang ke Liftoff.app/Contents/PlugIns/
cp "$HERE/build/Rewired_MacOS_orig.bundle" "$ORIG_BUNDLE"
cp "$HERE/build/Rewired_MacOS.bundle" "$TARGET_BUNDLE"
codesign --force --sign - "$ORIG_BUNDLE"
codesign --force --sign - "$TARGET_BUNDLE"

# 5. Aktifkan useAppleGameController di Rewired_Core.dll & Rewired_OSX.dll
LIFTOFF_MANAGED="/Users/fis/Library/Application Support/Steam/steamapps/common/Liftoff/Liftoff.app/Contents/Resources/Data/Managed"
if [ -d "$LIFTOFF_MANAGED" ]; then
    if [ ! -f "$LIFTOFF_MANAGED/Rewired_Core_orig.dll" ]; then
        cp "$LIFTOFF_MANAGED/Rewired_Core.dll" "$LIFTOFF_MANAGED/Rewired_Core_orig.dll"
    fi
    if [ -f "$LIFTOFF_MANAGED/Rewired_OSX_orig.dll" ]; then
        cp "$LIFTOFF_MANAGED/Rewired_OSX_orig.dll" "$LIFTOFF_MANAGED/Rewired_OSX.dll"
    fi
    python3 - "$LIFTOFF_MANAGED" << 'PYEOF'
import os, sys
managed = sys.argv[1]

core_orig = os.path.join(managed, "Rewired_Core_orig.dll")
core_dst  = os.path.join(managed, "Rewired_Core.dll")
with open(core_orig, "rb") as f:
    data = f.read()
pat_core = bytes.fromhex("06 1a 33 16 07 75 49 02 00 02 2d 02 16 2a 07 75 49 02 00 02 7b cf 0f 00 04 2a 16 2a")
rep_core = bytes.fromhex("06 1a 33 16 07 75 49 02 00 02 2d 02 16 2a 17 2a 00 00 00 00 00 00 00 00 00 2a 16 2a")
assert pat_core in data, "Pattern Rewired_Core.dll tidak ditemukan"
with open(core_dst, "wb") as f:
    f.write(data.replace(pat_core, rep_core, 1))
PYEOF
fi

echo "✅ Berhasil memasang plugin DJI RC 2 ke Liftoff.app!"
echo "   Lokasi: $TARGET_BUNDLE"
echo "   Backup: $ORIG_BUNDLE"
