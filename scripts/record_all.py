#!/usr/bin/env python3
"""
Record all six channels while you move each stick, then report the mapping.

Handy when a stick shows up under the wrong label: pushing the right stick
sideways moves the value the plugin calls yaw. The controller's firmware decides
the channel order, and a unit whose calibration differs can order them
differently, so the mapping in calib.json sometimes has to be rewritten.

Usage: start ./scripts/run.sh first, then run this and follow along.

    .venv/bin/python scripts/record_all.py
"""
import json
import os
import struct
import sys
import time

STATE_FILE = "/tmp/dji_rc2_state.bin"
FMT = "<IIdII6f6H6H6H6H"
SZ = struct.calcsize(FMT)
ROLES = ["roll", "pitch", "throttle", "yaw"]


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


def measure(seconds):
    acc = [[] for _ in range(6)]
    got = False
    t_end = time.time() + seconds
    while time.time() < t_end:
        u = read_state()
        if u and u[4]:
            got = True
            for i in range(6):
                acc[i].append(u[11 + i])
        time.sleep(0.02)
    if not got:
        return None
    return [int(round(sum(c) / len(c))) if c else 0 for c in acc]


def record(label, seconds=2.5):
    print(f"\n>>> {label}")
    for n in range(3, 0, -1):
        print(f"    mulai dalam {n}...", end="\r", flush=True)
        time.sleep(1)
    print("    REKAM! Gerakkan sekarang...      ", flush=True)
    r = measure(seconds)
    print("    selesai.                        ", flush=True)
    return r


def main():
    print("=" * 74)
    print("  RECORD ALL CHANNELS")
    print("=" * 74)
    print("  Pastikan ./scripts/run.sh jalan. Ikuti tiap langkah; ada hitungan")
    print("  3 detik sebelum merekam, jadi tunggu 'REKAM!' baru gerakkan.")
    print("=" * 74)

    input("\nTekan Enter untuk mulai (semua stick netral dulu)... ")
    neutral = measure(2.0)
    if not neutral:
        sys.exit("Tidak ada data. Pastikan ./scripts/run.sh jalan & remote tersambung.")
    print(f"  netral: {neutral}")

    trials = [
        ("roll",     "Gerakkan stick KANAN ke KIRI dan KANAN berulang"),
        ("pitch",    "Gerakkan stick KANAN ke ATAS dan BAWAH berulang"),
        ("throttle", "Gerakkan stick KIRI ke ATAS dan BAWAH berulang"),
        ("yaw",      "Gerakkan stick KIRI ke KIRI dan KANAN berulang"),
    ]

    result = {}
    for role, label in trials:
        r = record(label)
        if not r:
            print("    (tidak ada data)")
            continue
        deltas = [abs(r[i] - neutral[i]) for i in range(6)]
        order = sorted(range(6), key=lambda i: deltas[i], reverse=True)
        top, second = order[0], order[1]
        print(f"    netral {neutral} -> gerak {r}")
        print(f"    delta: {[deltas[i] for i in range(6)]}")
        if deltas[top] < 200:
            print("    ⚠️  tidak ada channel bergerak")
            continue
        print(f"    => {role} ada di raw[{top}] (delta {deltas[top]}), "
              f"pembanding raw[{second}] delta {deltas[second]}")
        result[role] = top

    print("\n" + "=" * 74)
    print("  HASIL")
    print("=" * 74)
    if not result:
        print("  Tidak ada yang terdeteksi.")
        return

    print(f"\n  {'role':<10} {'channel':<10}")
    print("  " + "-" * 24)
    for role in ROLES:
        ch = result.get(role)
        print(f"  {role:<10} {'raw[' + str(ch) + ']' if ch is not None else '?'}")

    used = [c for c in result.values()]
    if len(set(used)) != len(used):
        print("\n  ⚠️  Ada channel yang terpakai lebih dari satu role.")
        print("      Ulangi dan gerakkan HANYA satu stick tiap langkah.")

    print("\n  Blok \"mapping\" yang sesuai:")
    print()
    print('    "mapping": {')
    entries = []
    for role in ROLES:
        ch = result.get(role, {"roll": 0, "pitch": 1, "throttle": 2, "yaw": 3}[role])
        center = "false" if role == "throttle" else "true"
        entries.append(f'      "{role}":{" " * (12 - len(role))}'
                       f'{{ "source": {ch}, "invert": false, "center": {center} }}')
    entries.append('      "aux_left":   { "source": 4, "invert": false, "center": true }')
    entries.append('      "aux_right":  { "source": 5, "invert": false, "center": true }')
    print(",\n".join(entries))
    print("    }")
    print()
    print("  Tempel ke src/calib.json, lalu:")
    print("      ./scripts/install.sh && restart Liftoff")


if __name__ == "__main__":
    main()
