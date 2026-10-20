#!/usr/bin/env python3
"""
Check whether the DJI RC is reachable from libusb.

macOS can detect the controller (visible in ioreg) while libusb sees nothing at
all. That happens when the device requires a USB access entitlement the caller
does not have, and the symptom is confusing: the controller looks connected in
System Information, yet no data arrives.

Run this after replugging the controller. It compares what macOS knows against
what libusb can actually open, so it is clear whether the problem is the device
or the permissions.

    .venv/bin/python scripts/check_usb.py
"""
import subprocess
import sys

DJI_VID = 0x2CA3


def ioreg_devices():
    """Return the DJI devices macOS has enumerated, as (name, vid, pid)."""
    try:
        out = subprocess.run(
            ["ioreg", "-p", "IOUSB", "-l", "-w0"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        return []

    found = []
    current = None
    for line in out.splitlines():
        if "+-o " in line:
            current = line.split("+-o ", 1)[1].split("  <")[0].strip()
        if '"idVendor"' in line and current:
            try:
                vid = int(line.split("=", 1)[1].strip())
            except ValueError:
                continue
            if vid == DJI_VID:
                found.append(current)
                current = None
    return found


def main():
    print("=" * 68)
    print("  USB ACCESS CHECK")
    print("=" * 68)

    os_sees = ioreg_devices()
    print(f"\n1. macOS (ioreg) melihat {len(os_sees)} device DJI:")
    for name in os_sees:
        print(f"     - {name}")
    if not os_sees:
        print("     (tidak ada)")
        print("\n   Remote belum terdeteksi macOS.")
        print("   Cek: kabel USB-C data (bukan charge-only), port langsung,")
        print("   remote menyala, dan coba port USB-C yang lain.")
        return 1

    try:
        import usb.core
    except ImportError:
        print("\n   pyusb tidak terpasang. Jalankan: pip install -r requirements.txt")
        return 1

    all_devs = list(usb.core.find(find_all=True))
    print(f"\n2. libusb melihat {len(all_devs)} device total:")
    for d in all_devs:
        try:
            desc = f"{d.manufacturer} {d.product}"
        except Exception:
            desc = "(info tidak terbaca)"
        print(f"     - {d.idVendor:04x}:{d.idProduct:04x}  {desc}")

    dji = usb.core.find(idVendor=DJI_VID)
    print()
    if dji is None:
        print("3. HASIL: macOS melihat remote, tapi libusb TIDAK.")
        print()
        print("   Ini masalah izin, bukan kabel dan bukan kode plugin:")
        print("   macOS menandai device ini 'NeedsDeviceAccessEntitlement'.")
        print()
        print("   Yang bisa dicoba:")
        print("     a. Cabut, tunggu 5 detik, colok lagi ke port USB-C lain")
        print("        (langsung ke laptop, jangan lewat hub/dock).")
        print("     b. Restart remote, lalu colok ulang.")
        print("     c. Tutup aplikasi lain yang mungkin memegang USB")
        print("        (DJI Assistant, simulator, aplikasi DJI lain).")
        print("     d. Cabut-coloL saat Liftoff sudah tertutup, baru buka Liftoff.")
        print()
        return 1

    print(f"3. HASIL: remote DITEMUKAN oleh libusb  ({dji.idVendor:04x}:{dji.idProduct:04x})")
    print("   Akses USB sudah normal. Lanjutkan dengan:")
    print("       ./scripts/run.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
