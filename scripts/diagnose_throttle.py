#!/usr/bin/env python3
"""
Work out the real throttle direction from the device, not from assumptions.

Start ./scripts/run.sh in one terminal, then run this in another. The script
asks you to hold the LEFT stick fully up, fully down, then release it. From the
raw values it measures, it prints the exact block to paste into src/calib.json.

The DJI RC 2's left stick springs back to the middle, so this plugin treats it
as a unipolar throttle: released = 0, pushed up = 1. There is no negative
throttle, and pulling down does not subtract anything.

Why min/max get swapped instead of using "invert": if the channel counts the
wrong way, then the value recorded as "min" during calibration is really the
top of the stick, and "max" is really the bottom. Reflecting the raw value
afterwards cannot fix that, because the reference range is backwards too. The
only correct fix is to swap the two ends.
"""
import os
import struct
import sys
import time

STATE_FILE = "/tmp/dji_rc2_state.bin"
FMT = "<IIdII6f6H6H6H6H"
SZ = struct.calcsize(FMT)


def read_state():
    try:
        with open(STATE_FILE, "rb") as f:
            data = f.read(SZ)
    except FileNotFoundError:
        return None
    if len(data) < SZ:
        return None
    u = struct.unpack(FMT, data)
    return u if u[0] == 0x444A4932 else None


def hold_and_measure(label, seconds=2.5):
    """Average the raw throttle channel while the user holds a position."""
    while True:
        vals = []
        t_end = time.time() + seconds
        while time.time() < t_end:
            u = read_state()
            if u:
                vals.append(u[11 + 2])
            time.sleep(0.02)
        if not vals:
            print("    (belum ada data - pastikan ./scripts/run.sh jalan dan controller tersambung)")
            input("    Tekan Enter untuk coba lagi... ")
            continue
        return min(vals), max(vals), sum(vals) / len(vals)


def main():
    print("=" * 72)
    print("  THROTTLE DIRECTION CHECK")
    print("  Pastikan ./scripts/run.sh sudah jalan dan controller tersambung.")
    print("  JadiRelaks saja, ikuti instruksinya satu per satu.")
    print("=" * 72)

    input("\n>>> Pegang stick KIRI mentok ke ATAS, tahan. Lalu tekan Enter... ")
    up = hold_and_measure("ATAS")
    print(f"    raw channel throttle saat ATAS  : {up[2]:>6.0f}   (rentang {up[0]}..{up[1]})")

    input("\n>>> Sekarang pegang stick KIRI mentok ke BAWAH, tahan. Tekan Enter... ")
    down = hold_and_measure("BAWAH")
    print(f"    raw channel throttle saat BAWAH : {down[2]:>6.0f}   (rentang {down[0]}..{down[1]})")

    input("\n>>> Terakhir, LEPAS stick (posisi netral). Tekan Enter... ")
    mid = hold_and_measure("NETRAL")
    print(f"    raw channel throttle saat NETRAL: {mid[2]:>6.0f}   (rentang {mid[0]}..{mid[1]})")

    raw_up, raw_down, raw_mid = up[2], down[2], mid[2]

    print("\n" + "=" * 72)
    print("  HASIL")
    print("=" * 72)
    print(f"  stick ATAS   -> raw {raw_up:.0f}")
    print(f"  stick NETRAL -> raw {raw_mid:.0f}")
    print(f"  stick BAWAH  -> raw {raw_down:.0f}")

    if abs(raw_up - raw_down) < 200:
        print("\n  raw hampir tidak berubah antara atas dan bawah.")
        print("  Kemungkinan channel ini BUKAN throttle di perangkat ini.")
        print("  Jalankan: ./scripts/run.sh --identify")
        return

    inverted = raw_down > raw_up
    print()
    if inverted:
        print("  Arah channel: KEBALIK (raw naik saat stick diturunkan)")
        print("  -> kalibrasi min/max perlu DITUKAR")
    else:
        print("  Arah channel: NORMAL (raw naik saat stick dinaikkan)")

    print("\n  Blok siap tempel untuk src/calib.json, bagian \"axes\" -> \"throttle\":")
    print()
    if inverted:
        print('    "throttle": {')
        print('      "offset": 5,')
        print(f'      "min": {raw_down:.0f},')
        print(f'      "center": {raw_mid:.0f},')
        print(f'      "max": {raw_up:.0f}')
        print('    }')
    else:
        print('    "throttle": {')
        print('      "offset": 5,')
        print(f'      "min": {raw_down:.0f},')
        print(f'      "center": {raw_mid:.0f},')
        print(f'      "max": {raw_up:.0f}')
        print('    }')
    print()
    print("  Setelah itu:")
    print("      ./scripts/install.sh      (rebuild + pasang plugin)")
    print("      lalu restart Liftoff")
    print()
    print("  Catatan: \"center\" tidak dipakai untuk throttle (mode unipolar),")
    print("  jadi nilainya hanya untuk kelengkapan file.")
    print()
    print("  Kalau 'min' lebih besar dari 'max', itu memang benar untuk channel")
    print("  kebalik dan akan dibaca apa adanya oleh plugin.")


if __name__ == "__main__":
    main()
