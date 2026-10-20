#!/usr/bin/env python3
"""
Record what the controller actually reports while you move each input.

Run ./scripts/run.sh in one terminal (Liftoff closed is fine), then run this in
another. It walks through each stick, records the raw values at both ends, and
prints what direction the plugin would produce. That makes it obvious whether a
stick is wired backwards before you go near the configuration.
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

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


def measure(seconds=1.5):
    """Return (raw[6], values[6]) averaged over a short hold."""
    raws = [[] for _ in range(6)]
    vals = [[] for _ in range(6)]
    t_end = time.time() + seconds
    got = False
    while time.time() < t_end:
        u = read_state()
        if u and u[4]:
            got = True
            for i in range(6):
                raws[i].append(u[11 + i])
                vals[i].append(u[5 + i])
        time.sleep(0.02)
    if not got:
        return None, None
    r = [int(round(sum(c) / len(c))) for c in raws]
    v = [sum(c) / len(c) for c in vals]
    return r, v


def step(prompt):
    while True:
        input(f">>> {prompt} Tahan, lalu Enter... ")
        r, v = measure()
        if r:
            return r, v
        print("    (belum ada data - pastikan ./scripts/run.sh jalan dan remote tersambung)")


def main():
    print("=" * 72)
    print("  RECORD STICK DIRECTIONS")
    print("  Pastikan ./scripts/run.sh jalan di terminal lain.")
    print("=" * 72)

    n_raw, _ = step("LEPAS semua stick (netral)")
    raw_neutral = n_raw
    print(f"    raw netral: {raw_neutral}")

    checks = [
        ("throttle", 2, "Dorong stick KIRI mentok ke ATAS",
         "Tarik stick KIRI mentok ke BAWAH",
         "atas harus memberi nilai LEBIH BESAR"),
        ("roll", 0, "Dorong stick KANAN mentok ke KIRI",
         "Dorong stick KANAN mentok ke KANAN",
         "kanan harus memberi nilai LEBIH BESAR"),
        ("pitch", 1, "Dorong stick KANAN mentok ke ATAS",
         "Tarik stick KANAN mentok ke BAWAH",
         "atas harus memberi nilai LEBIH BESAR"),
        ("yaw", 3, "Dorong stick KIRI mentok ke KIRI",
         "Dorong stick KIRI mentok ke KANAN",
         "kanan harus memberi nilai LEBIH BESAR"),
    ]

    print("\n" + "=" * 72)
    print("  HASIL")
    print("=" * 72)

    swapped = []
    for role, ch, prompt_a, prompt_b, note in checks:
        ra, va = step(prompt_a)
        rb, vb = step(prompt_b)
        a, b = ra[ch], rb[ch]
        print(f"\n  {role} (raw[{ch}]):")
        print(f"    {note}")
        print(f"    A={a}  B={b}   (span {abs(b-a)})")
        if abs(b - a) < 200:
            print("    ⚠️  span terlalu kecil - channel ini mungkin bukan axis ini")
            continue
        if b > a:
            print("    ✅ arah SUDAH BENAR")
        else:
            print("    ❌ arah TERBALIK - perlu tukar min<->max")
            swapped.append(role)

    print("\n" + "=" * 72)
    if not swapped:
        print("  Semua arah sudah benar.")
    else:
        print(f"  Perlu diperbaiki: {', '.join(swapped)}")
        print()
        print("  Jalankan kalibrasi ulang (sudah mengukur arah sendiri):")
        print("      ./scripts/run.sh --calibrate")
    print("=" * 72)


if __name__ == "__main__":
    main()
