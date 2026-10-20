#!/usr/bin/env python3
"""
Find out which raw channel each physical input really belongs to.

The plugin ships with a default channel mapping, but a controller whose
calibration or firmware differs can wire the sticks to different channels. When
that happens a stick shows up under the wrong name: pushing the right stick
sideways moves the value labelled yaw, for instance.

This records all six channels at once while you hold each input in turn, then
reports which channel moved for each one and prints a mapping block ready to
paste into src/calib.json.

Run ./scripts/run.sh in one terminal first, then this in another:

    .venv/bin/python scripts/identify_channels.py
"""
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

STATE_FILE = "/tmp/dji_rc2_state.bin"
FMT = "<IIdII6f6H6H6H6H"
SZ = struct.calcsize(FMT)
CALIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "calib.json")

# role -> how the user should move the stick
STEPS = [
    ("throttle", "Dorong stick KIRI mentok ke ATAS"),
    ("yaw",      "Dorong stick KIRI mentok ke KIRI (atau KANAN, pilih satu arah)"),
    ("roll",     "Dorong stick KANAN mentok ke KANAN"),
    ("pitch",    "Dorong stick KANAN mentok ke ATAS"),
]


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


def measure(seconds=1.5):
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


def hold(prompt):
    while True:
        input(f">>> {prompt} Tahan, lalu Enter... ")
        r = measure()
        if r:
            return r
        print("    (belum ada data - pastikan ./scripts/run.sh jalan & remote tersambung)")


def main():
    print("=" * 74)
    print("  IDENTIFY CHANNELS - channel mana milik input mana")
    print("  Pastikan ./scripts/run.sh jalan di terminal lain.")
    print("=" * 74)

    neutral = hold("LEPAS semua stick (netral)")
    print(f"    netral: {neutral}\n")

    found = {}
    for role, prompt in STEPS:
        r = hold(prompt)
        moved = [(abs(r[i] - neutral[i]), i) for i in range(6)]
        moved.sort(reverse=True)
        delta, ch = moved[0]
        print(f"    raw: {r}")
        if delta < 200:
            print(f"    ⚠️  tidak ada channel yang bergerak cukup jauh")
            continue
        print(f"    -> bergerak di raw[{ch}] (selisih {delta})")
        if ch in found:
            print(f"    ⚠️  raw[{ch}] sudah dipakai oleh '{found[ch]}' - pastikan")
            print(f"        hanya satu stick yang digerakkan tiap langkah.")
        found[ch] = role
        found[role] = (ch, neutral[ch], r[ch])

    print("\n" + "=" * 74)
    print("  HASIL")
    print("=" * 74)
    mapping = {}
    for role, prompt in STEPS:
        if role not in found:
            print(f"  {role:<10} tidak terdeteksi")
            continue
        ch, n, m = found[role]
        # Larger raw should mean "more positive": up for throttle/pitch, right
        # for roll and yaw. If it does not, the ends in the calibration are the
        # other way round and the plugin needs them swapped.
        invert = (m < n)
        mapping[role] = {"source": ch, "invert": False, "center": role != "throttle"}
        print(f"  {role:<10} <- raw[{ch}]   (netral {n}, gerak {m})"
              f"{'   [arah terbalik]' if invert else ''}")

    print()
    print("  Blok \"mapping\" untuk src/calib.json:")
    print()
    print('    "mapping": {')
    entries = dict(mapping)
    entries["aux_left"] = {"source": 4, "invert": False, "center": True}
    entries["aux_right"] = {"source": 5, "invert": False, "center": True}
    order = ["roll", "pitch", "throttle", "yaw", "aux_left", "aux_right"]
    for i, role in enumerate(order):
        e = entries[role]
        comma = "," if i < len(order) - 1 else ""
        print(f'      "{role}": {{ "source": {e["source"]}, '
              f'"invert": {str(e["invert"]).lower()}, '
              f'"center": {str(e["center"]).lower()} }}{comma}')
    print("    }")
    print()
    print("  Setelah menempel, jalankan:")
    print("      ./scripts/install.sh && restart Liftoff")
    print()
    print("  Kalau sebuah channel ditandai [arah terbalik], tukar min<->max")
    print("  untuk axis itu di blok \"axes\".")


if __name__ == "__main__":
    main()
