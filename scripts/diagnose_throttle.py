#!/usr/bin/env python3
"""
Diagnose the throttle direction.

Run this with the controller plugged in, then follow the prompts:
move the LEFT stick fully up, fully down, and release it, holding each
position for a moment. The script prints the raw value and the calibrated
value continuously so you can see exactly which way the channel moves.
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

STATE_FILE = "/tmp/dji_rc2_state.bin"
FMT = "<IIdII6f6H6H6H6H"
SZ = struct.calcsize(FMT)

AXIS = ["roll", "pitch", "throttle", "yaw", "wl", "wr"]


def main():
    print("=" * 72)
    print("  THROTTLE DIAGNOSTIC")
    print("  Gerakkan stick KIRI ke: ATAS mentok -> diam sebentar ->")
    print("  BAWAH mentok -> diam sebentar -> LEPAS (netral) -> diam sebentar")
    print("  Tekan Ctrl+C untuk berhenti.")
    print("=" * 72)
    print()
    print(f"{'waktu':>6} | {'raw[2]':>8} | {'throttle terkirim':>17} | {'min':>6} {'ctr':>6} {'max':>6}")
    print("-" * 72)

    t0 = time.time()
    last_print = 0.0
    try:
        while True:
            try:
                with open(STATE_FILE, "rb") as f:
                    data = f.read(SZ)
            except FileNotFoundError:
                print("Menunggu /tmp/dji_rc2_state.bin ... jalankan ./scripts/run.sh dulu")
                time.sleep(0.5)
                continue
            if len(data) < SZ:
                time.sleep(0.05)
                continue
            u = struct.unpack(FMT, data)
            magic, ver, ts, pid, conn = u[:5]
            if magic != 0x444A4932 or not conn:
                print("Menunggu data controller ...")
                time.sleep(0.5)
                continue

            thr = u[7]
            raw = u[11:17]
            cmin = u[17:23]
            cctr = u[23:29]
            cmax = u[29:35]

            now = time.time()
            if now - last_print >= 0.20:
                last_print = now
                age = now - ts
                flag = " (data basi!)" if age > 0.5 else ""
                print(f"{now-t0:>6.1f} | {raw[2]:>8} | {thr:>17.3f} | "
                      f"{cmin[2]:>6} {cctr[2]:>6} {cmax[2]:>6}{flag}")
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\n\nSelesai.")
        print("\nCara membaca hasilnya:")
        print("  - Kalau saat stick ATAS mentok raw[2] paling KECIL, berarti channel kebalik.")
        print("  - Kalau saat stick ATAS mentok raw[2] paling BESAR, berarti channel normal.")
        print("  - Lihat juga kolom min/ctr/max: apakah masuk akal dengan arah gerakan.")


if __name__ == "__main__":
    main()
