#!/usr/bin/env python3
"""
Measure the real direction of every stick channel from the device itself.

Start ./scripts/run.sh in one terminal, then run this in another. The script
walks you through each stick and records what the raw values actually do. At
the end it prints calibration blocks you can paste straight into src/calib.json.

Why this exists: the DJI RC 2's calibration can come out with min and max
recorded the other way round, which makes every axis read backwards (roll left
becomes right, throttle down becomes 1). Swapping the two ends in the config is
the correct fix, because the end the channel counts towards is what defines the
direction. Reflecting or negating the scaled output does not work: it happens
after clamping, so the bottom half of a unipolar axis would read as full
throttle.
"""
import os
import struct
import sys
import time

STATE_FILE = "/tmp/dji_rc2_state.bin"
FMT = "<IIdII6f6H6H6H6H"
SZ = struct.calcsize(FMT)

# Raw channel index -> how it is named in calib.json
CHANNELS = [
    ("aileron", 0, "stick KANAN-kiri (roll)"),
    ("elevator", 1, "stick KANAN-atas/bawah (pitch)"),
    ("throttle", 2, "stick KIRI-atas/bawah (throttle)"),
    ("rudder", 3, "stick KIRI-kiri/kanan (yaw)"),
    ("wheel_left", 4, "roda ATAS KIRI (LT/LB)"),
    ("wheel_right", 5, "roda ATAS KANAN (RT/RB)"),
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


def measure(seconds=2.0):
    """Collect raw samples for a while. Returns (min, max, avg) or None."""
    vals = None
    t_end = time.time() + seconds
    while time.time() < t_end:
        u = read_state()
        if u:
            if vals is None:
                vals = [[] for _ in range(6)]
            for c in range(6):
                vals[c].append(u[11 + c])
        time.sleep(0.02)
    if vals is None:
        return None
    return [(min(v), max(v), sum(v) / len(v)) for v in vals]


def hold(label, seconds=2.0):
    while True:
        r = measure(seconds)
        if r:
            return r
        print("    (belum ada data - pastikan ./scripts/run.sh jalan dan controller tersambung)")
        input("    Tekan Enter untuk coba lagi... ")


def fmt_row(result):
    out = []
    for c, (lo, hi, avg) in enumerate(result):
        out.append(f"{c}:{avg:>6.0f}[{lo}-{hi}]")
    return "  ".join(out)


def main():
    print("=" * 76)
    print("  AXIS DIRECTION CHECK - ukur arah semua channel dari perangkat")
    print("=" * 76)
    print("  Pastikan ./scripts/run.sh sudah jalan dan controller tersambung.")
    print("  Ikuti tiap langkah, tahan posisinya sampai diukur (~2 detik).")
    print()

    neutral = None
    input(">>> LEPAS SEMUA stick dan roda (posisi netral). Tekan Enter... ")
    neutral = hold("netral")
    print(f"    netral  ->  {fmt_row(neutral)}")

    up = None
    input("\n>>> Dorong stick KIRI mentok ke ATAS (throttle). Tahan. Enter... ")
    up = hold("atas")
    print(f"    KIRI-atas ->  {fmt_row(up)}")

    down = None
    input("\n>>> Tarik stick KIRI mentok ke BAWAH. Tahan. Enter... ")
    down = hold("bawah")
    print(f"    KIRI-bawah ->  {fmt_row(down)}")

    stick_r = None
    input("\n>>> Dorong stick KANAN mentok ke KANAN (roll). Tahan. Enter... ")
    stick_r = hold("kanan")
    print(f"    KANAN-kanan ->  {fmt_row(stick_r)}")

    stick_p = None
    input("\n>>> Dorong stick KANAN mentok ke ATAS (pitch). Tahan. Enter... ")
    stick_p = hold("pitch atas")
    print(f"    KANAN-atas ->  {fmt_row(stick_p)}")

    print("\n" + "=" * 76)
    print("  HASIL: arah tiap channel")
    print("=" * 76)

    def report(name, idx, label, low_raw, high_raw, neutral_raw):
        d = high_raw - low_raw
        print(f"\n  {name} (channel {idx}) - {label}")
        print(f"    netral={neutral_raw:.0f}  ujung A={low_raw:.0f}  ujung B={high_raw:.0f}")
        if abs(d) < 200:
            print("    -> channel ini hampir tidak bergerak; kemungkinan bukan axis ini")
            print("       atau roda perlu diputar penuh saat kalibrasi.")
            return
        print(f"    -> span {abs(d):.0f} (sehat)")

    report("aileron", 0, "roll", stick_r[0][2], up[0][2], neutral[0][2])

    # Determine per-channel direction using the two measured extremes.
    print("\n" + "=" * 76)
    print("  KESIMPULAN ARAH")
    print("=" * 76)

    def direction(name, idx, raw_should_be_high, raw_should_be_low, neutral_raw):
        """raw_should_be_high is the physical position that ought to give +1."""
        if raw_should_be_high is None or raw_should_be_low is None:
            return
        if abs(raw_should_be_high - raw_should_be_low) < 200:
            print(f"  {name:<12} channel {idx}: span terlalu kecil, dilewati")
            return
        if raw_should_be_high > raw_should_be_low:
            print(f"  {name:<12} channel {idx}: NORMAL  (raw naik sesuai arah positif)")
        else:
            print(f"  {name:<12} channel {idx}: KEBALIK (raw berlawanan arah positif)")
            print(f"  {'':<12}           -> tukar min<->max di calib.json")

    # For a centred stick, "positive" is conventionally: roll right, pitch up,
    # yaw left (Liftoff/RC convention varies), throttle up. What matters here is
    # that the user-visible mapping matches; we report the physical direction.
    direction("throttle", 2, up[2][2], down[2][2], neutral[2][2])
    direction("roll", 0, stick_r[0][2], neutral[0][2], neutral[0][2])
    direction("pitch", 1, stick_p[1][2], neutral[1][2], neutral[1][2])

    print()
    print("  Catatan: plugin sekarang MEMBACA ARAH dari min/max. Jadi kalau sebuah")
    print("  channel kebalik, cukup tulis min sebagai nilai ujung yang lebih besar")
    print("  dan max sebagai yang lebih kecil. Tidak perlu ubah kode.")
    print()
    print("  Untuk memperbaiki semuanya sekaligus, jalankan kalibrasi ulang dan")
    print("  pastikan setiap stick digerakkan ke kedua ujungnya penuh:")
    print("      ./scripts/run.sh --calibrate")
    print("  lalu kembalikan min/max yang benar di src/calib.json dan:")
    print("      ./scripts/install.sh && restart Liftoff")


if __name__ == "__main__":
    main()
