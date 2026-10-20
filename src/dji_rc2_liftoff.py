#!/usr/bin/env python3
"""
DJI RC 2 (Mini 5 Pro / Air 3 / Mini 4 Pro) -> macOS Liftoff Bridge & Monitor.

Works seamlessly with the Rewired_MacOS.bundle plugin installed in Liftoff.app:
- Polls DJI RC 2 (USB VID 0x2ca3, PID 0x1021) via DUML (cmd_set=0x06, cmd_id=0xf5)
  at ~240 Hz without requiring root/sudo or Android ADB unlocking.
- Automatically fetches factory stick calibration from the controller's MCU
  via DUML cmd_set=0x06, cmd_id=0x38 (or loads/saves calib.json).
- Shares live state via /tmp/dji_rc2_state.bin with Liftoff's Rewired_MacOS.bundle.
  If Liftoff is already running and polling USB directly, this script automatically
  switches to passive shared-memory monitor mode so there is never a USB conflict.
"""

import ctypes
import json
import mmap
import os
import struct
import sys
import time

# Ensure Homebrew libusb is discoverable on Apple Silicon & Intel Macs
for libpath in ("/opt/homebrew/lib/libusb-1.0.dylib", "/usr/local/lib/libusb-1.0.dylib"):
    if os.path.exists(libpath):
        os.environ.setdefault("DYLD_LIBRARY_PATH", os.path.dirname(libpath))
        break

import usb.core
import usb.util

STATE_FILE_PATH = "/tmp/dji_rc2_state.bin"
HERE = os.path.dirname(os.path.abspath(__file__))
CALIB_FILE_PATH = os.path.join(HERE, "calib.json")

STATE_MAGIC = 0x444A4932  # 'DJI2'
STATE_VERSION = 1
STATE_STRUCT_FMT = "<IIdII6f6H6H6H6H"
STATE_STRUCT_SIZE = struct.calcsize(STATE_STRUCT_FMT)

DJI_VID = 0x2CA3
DEVICES = [
    {"name": "DJI RC 2 (rc331)", "pid": 0x1021, "iface": 0, "ep_out": 0x01, "ep_in": 0x81},
    {"name": "DJI RC (rm330)",   "pid": 0x1023, "iface": 1, "ep_out": 0x02, "ep_in": 0x83},
]

CRC8_TABLE = [
    0x00,0x5e,0xbc,0xe2,0x61,0x3f,0xdd,0x83,0xc2,0x9c,0x7e,0x20,0xa3,0xfd,0x1f,0x41,
    0x9d,0xc3,0x21,0x7f,0xfc,0xa2,0x40,0x1e,0x5f,0x01,0xe3,0xbd,0x3e,0x60,0x82,0xdc,
    0x23,0x7d,0x9f,0xc1,0x42,0x1c,0xfe,0xa0,0xe1,0xbf,0x5d,0x03,0x80,0xde,0x3c,0x62,
    0xbe,0xe0,0x02,0x5c,0xdf,0x81,0x63,0x3d,0x7c,0x22,0xc0,0x9e,0x1d,0x43,0xa1,0xff,
    0x46,0x18,0xfa,0xa4,0x27,0x79,0x9b,0xc5,0x84,0xda,0x38,0x66,0xe5,0xbb,0x59,0x07,
    0xdb,0x85,0x67,0x39,0xba,0xe4,0x06,0x58,0x19,0x47,0xa5,0xfb,0x78,0x26,0xc4,0x9a,
    0x65,0x3b,0xd9,0x87,0x04,0x5a,0xb8,0xe6,0xa7,0xf9,0x1b,0x45,0xc6,0x98,0x7a,0x24,
    0xf8,0xa6,0x44,0x1a,0x99,0xc7,0x25,0x7b,0x3a,0x64,0x86,0xd8,0x5b,0x05,0xe7,0xb9,
    0x8c,0xd2,0x30,0x6e,0xed,0xb3,0x51,0x0f,0x4e,0x10,0xf2,0xac,0x2f,0x71,0x93,0xcd,
    0x11,0x4f,0xad,0xf3,0x70,0x2e,0xcc,0x92,0xd3,0x8d,0x6f,0x31,0xb2,0xec,0x0e,0x50,
    0xaf,0xf1,0x13,0x4d,0xce,0x90,0x72,0x2c,0x6d,0x33,0xd1,0x8f,0x0c,0x52,0xb0,0xee,
    0x32,0x6c,0x8e,0xd0,0x53,0x0d,0xef,0xb1,0xf0,0xae,0x4c,0x12,0x91,0xcf,0x2d,0x73,
    0xca,0x94,0x76,0x28,0xab,0xf5,0x17,0x49,0x08,0x56,0xb4,0xea,0x69,0x37,0xd5,0x8b,
    0x57,0x09,0xeb,0xb5,0x36,0x68,0x8a,0xd4,0x95,0xcb,0x29,0x77,0xf4,0xaa,0x48,0x16,
    0xe9,0xb7,0x55,0x0b,0x88,0xd6,0x34,0x6a,0x2b,0x75,0x97,0xc9,0x4a,0x14,0xf6,0xa8,
    0x74,0x2a,0xc8,0x96,0x15,0x4b,0xa9,0xf7,0xb6,0xe8,0x0a,0x54,0xd7,0x89,0x6b,0x35,
]

CRC16_TABLE = [
    0x0000,0x1189,0x2312,0x329b,0x4624,0x57ad,0x6536,0x74bf,
    0x8c48,0x9dc1,0xaf5a,0xbed3,0xca6c,0xdbe5,0xe97e,0xf8f7,
    0x1081,0x0108,0x3393,0x221a,0x56a5,0x472c,0x75b7,0x643e,
    0x9cc9,0x8d40,0xbfdb,0xae52,0xdaed,0xcb64,0xf9ff,0xe876,
    0x2102,0x308b,0x0210,0x1399,0x6726,0x76af,0x4434,0x55bd,
    0xad4a,0xbcc3,0x8e58,0x9fd1,0xeb6e,0xfae7,0xc87c,0xd9f5,
    0x3183,0x200a,0x1291,0x0318,0x77a7,0x662e,0x54b5,0x453c,
    0xbdcb,0xac42,0x9ed9,0x8f50,0xfbef,0xea66,0xd8fd,0xc974,
    0x4204,0x538d,0x6116,0x709f,0x0420,0x15a9,0x2732,0x36bb,
    0xce4c,0xdfc5,0xed5e,0xfcd7,0x8868,0x99e1,0xab7a,0xbaf3,
    0x5285,0x430c,0x7197,0x601e,0x14a1,0x0528,0x37b3,0x263a,
    0xdecd,0xcf44,0xfddf,0xec56,0x98e9,0x8960,0xbbfb,0xaa72,
    0x6306,0x728f,0x4014,0x519d,0x2522,0x34ab,0x0630,0x17b9,
    0xef4e,0xfec7,0xcc5c,0xddd5,0xa96a,0xb8e3,0x8a78,0x9bf1,
    0x7387,0x620e,0x5095,0x411c,0x35a3,0x242a,0x16b1,0x0738,
    0xffcf,0xee46,0xdcdd,0xcd54,0xb9eb,0xa862,0x9af9,0x8b70,
    0x8408,0x9581,0xa71a,0xb693,0xc22c,0xd3a5,0xe13e,0xf0b7,
    0x0840,0x19c9,0x2b52,0x3adb,0x4e64,0x5fed,0x6d76,0x7cff,
    0x9489,0x8500,0xb79b,0xa612,0xd2ad,0xc324,0xf1bf,0xe036,
    0x18c1,0x0948,0x3bd3,0x2a5a,0x5ee5,0x4f6c,0x7df7,0x6c7e,
    0xa50a,0xb483,0x8618,0x9791,0xe32e,0xf2a7,0xc03c,0xd1b5,
    0x2942,0x38cb,0x0a50,0x1bd9,0x6f66,0x7eef,0x4c74,0x5dfd,
    0xb58b,0xa402,0x9699,0x8710,0xf3af,0xe226,0xd0bd,0xc134,
    0x39c3,0x284a,0x1ad1,0x0b58,0x7fe7,0x6e6e,0x5cf5,0x4d7c,
    0xc60c,0xd785,0xe51e,0xf497,0x8028,0x91a1,0xa33a,0xb2b3,
    0x4a44,0x5bcd,0x6956,0x78df,0x0c60,0x1de9,0x2f72,0x3efb,
    0xd68d,0xc704,0xf59f,0xe416,0x90a9,0x8120,0xb3bb,0xa232,
    0x5ac5,0x4b4c,0x79d7,0x685e,0x1ce1,0x0d68,0x3ff3,0x2e7a,
    0xe70e,0xf687,0xc41c,0xd595,0xa12a,0xb0a3,0x8238,0x93b1,
    0x6b46,0x7acf,0x4854,0x59dd,0x2d62,0x3ceb,0x0e70,0x1ff9,
    0xf78f,0xe606,0xd49d,0xc514,0xb1ab,0xa022,0x92b9,0x8330,
    0x7bc7,0x6a4e,0x58d5,0x495c,0x3de3,0x2c6a,0x1ef1,0x0f78,
]

AXIS_NAMES = ["aileron", "elevator", "throttle", "rudder", "wheel_left", "wheel_right"]
AXIS_OFFSETS = [1, 3, 5, 7, 9, 11]

# A range narrower than this means the channel never actually moved while it was
# being calibrated, so the numbers are just ADC noise. Scaling by such a range
# would amplify a couple of LSB into full-scale swings.
MIN_USABLE_SPAN = 200

# Fallback calibration, used when a channel's measured range is unusable.
DEFAULT_CAL = (
    [479, 507, 533, 481, 494, 504],
    [1642, 1707, 1701, 1612, 1732, 1745],
    [2864, 2874, 2826, 2789, 2732, 2755],
)


def crc8(data: bytes) -> int:
    c = 0x77
    for b in data:
        c = CRC8_TABLE[c ^ b]
    return c


def crc16(data: bytes) -> int:
    c = 0x3692
    for b in data:
        c = (c >> 8) ^ CRC16_TABLE[(c ^ b) & 0xFF]
    return c


def build_duml(sender: int, receiver: int, seq: int, cmd_type: int, cmd_set: int, cmd_id: int, payload: bytes = b"") -> bytes:
    length = 13 + len(payload)
    tag = (1 << 10) | (length & 0x3FF)
    hdr3 = bytes([0x55, tag & 0xFF, (tag >> 8) & 0xFF])
    head = hdr3 + bytes([
        crc8(hdr3),
        sender & 0xFF,
        receiver & 0xFF,
        seq & 0xFF,
        (seq >> 8) & 0xFF,
        cmd_type & 0xFF,
        cmd_set & 0xFF,
        cmd_id & 0xFF,
    ])
    body = head + payload
    c16 = crc16(body)
    return body + bytes([c16 & 0xFF, (c16 >> 8) & 0xFF])


def split_packets(buf: bytes):
    out = []
    i = 0
    n = len(buf)
    while i + 13 <= n:
        if buf[i] != 0x55:
            i += 1
            continue
        plen = buf[i + 1] | ((buf[i + 2] & 0x03) << 8)
        if plen < 13 or plen > 512 or crc8(buf[i : i + 3]) != buf[i + 3]:
            i += 1
            continue
        if i + plen > n:
            break
        pkt = bytes(buf[i : i + plen])
        if crc16(pkt[:-2]) == (pkt[-2] | (pkt[-1] << 8)):
            out.append(pkt)
        i += plen
    return out, buf[i:]


def scale_axis(raw: int, lo: int, ctr: int, hi: int, deadzone: float = 0.025) -> float:
    """Bipolar scaling for self-centering sticks: center -> 0.0."""
    if raw >= ctr:
        span = max(1, hi - ctr)
        frac = (raw - ctr) / span
    else:
        span = max(1, ctr - lo)
        frac = (raw - ctr) / span
    a = abs(frac)
    if a <= deadzone:
        return 0.0
    sign = 1.0 if frac >= 0.0 else -1.0
    scaled = sign * ((a - deadzone) / (1.0 - deadzone))
    return max(-1.0, min(1.0, scaled))


def scale_axis_unipolar(raw: int, lo: int, ctr: int, hi: int) -> float:
    """Unipolar scaling for a self-centering throttle, which is what the DJI RC 2
    has (the stick springs back to the middle when released).

    The released/centered position is treated as throttle 0, and pushing up
    raises it to 1. Pulling down stays at 0 instead of going negative, since
    Liftoff has no use for negative throttle."""
    span = hi - ctr
    if span <= 0:
        return 0.0
    frac = (raw - ctr) / span
    return max(0.0, min(1.0, frac))


def bar(val: float, width: int = 20, bipolar: bool = True) -> str:
    """Render a horizontal indicator. Bipolar values (-1..1) put zero in the
    middle; unipolar values (0..1) fill from the left."""
    if bipolar:
        pos = int(round((val + 1.0) * 0.5 * width))
        zero = width // 2
    else:
        pos = int(round(val * width))
        zero = 0
    pos = max(0, min(width, pos))
    chars = ["─"] * (width + 1)
    chars[zero] = "┼"
    chars[pos] = "█"
    return "".join(chars)


def open_shm():
    fd = os.open(STATE_FILE_PATH, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        os.fchmod(fd, 0o666)
    except OSError:
        pass
    if os.fstat(fd).st_size < STATE_STRUCT_SIZE:
        os.write(fd, b"\x00" * STATE_STRUCT_SIZE)
    mm = mmap.mmap(fd, STATE_STRUCT_SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    os.close(fd)
    return mm


def load_calib():
    cal_min = [479, 507, 533, 481, 494, 504]
    cal_ctr = [1642, 1707, 1701, 1612, 1732, 1745]
    cal_max = [2864, 2874, 2826, 2789, 2732, 2755]
    if os.path.exists(CALIB_FILE_PATH):
        try:
            with open(CALIB_FILE_PATH) as f:
                data = json.load(f)
            axes = data.get("axes", {})
            for i, name in enumerate(AXIS_NAMES):
                if name not in axes:
                    continue
                mn = int(axes[name]["min"])
                ct = int(axes[name]["center"])
                mx = int(axes[name]["max"])
                # Ignore narrow/inconsistent ranges; keep the fallback instead.
                if mn < ct < mx and (mx - mn) >= MIN_USABLE_SPAN:
                    cal_min[i], cal_ctr[i], cal_max[i] = mn, ct, mx
        except Exception:
            pass
    return cal_min, cal_ctr, cal_max


DEFAULT_MAPPING = {
    "roll":      {"source": 0, "invert": False, "center": True},
    "pitch":     {"source": 1, "invert": True,  "center": True},
    "throttle":  {"source": 2, "invert": False, "center": False},
    "yaw":       {"source": 3, "invert": False, "center": True},
    "aux_left":  {"source": 4, "invert": False, "center": True},
    "aux_right": {"source": 5, "invert": False, "center": True},
}


def save_calib(dev_info, cal_min, cal_ctr, cal_max):
    # Guard against ranges measured while the channel never actually moved.
    # A span of a few LSB is pure noise and would make the axis jump wildly.
    rejected = []
    for i, name in enumerate(AXIS_NAMES):
        span = cal_max[i] - cal_min[i]
        if span < MIN_USABLE_SPAN or not (cal_min[i] < cal_ctr[i] < cal_max[i]):
            rejected.append((name, span))
            cal_min[i] = DEFAULT_CAL[0][i]
            cal_ctr[i] = DEFAULT_CAL[1][i]
            cal_max[i] = DEFAULT_CAL[2][i]

    if rejected:
        print("\n⚠️  Channel berikut tidak bergerak cukup jauh saat kalibrasi,")
        print("    jadi nilainya dibuang dan diganti default:")
        for name, span in rejected:
            print(f"      {name:<12} span={span} (minimal {MIN_USABLE_SPAN})")
        print("    Putar/pindahkan input itu sampai mentok, lalu kalibrasi ulang.")

    axes = {}
    for i, name in enumerate(AXIS_NAMES):
        axes[name] = {
            "offset": AXIS_OFFSETS[i],
            "min": int(cal_min[i]),
            "center": int(cal_ctr[i]),
            "max": int(cal_max[i]),
        }

    # Preserve any user-tuned axis mapping instead of clobbering it.
    mapping = dict(DEFAULT_MAPPING)
    if os.path.exists(CALIB_FILE_PATH):
        try:
            with open(CALIB_FILE_PATH) as f:
                existing = json.load(f).get("mapping")
            if isinstance(existing, dict):
                for key, val in existing.items():
                    if isinstance(val, dict):
                        mapping[key] = val
        except Exception:
            pass

    cfg = {
        "device": dev_info["name"],
        "vid": DJI_VID,
        "pid": dev_info["pid"],
        "interface": dev_info["iface"],
        "ep_out": dev_info["ep_out"],
        "ep_in": dev_info["ep_in"],
        "cmd_set": 6,
        "cmd_id": 245,
        "src": 6,
        "payload_len": 13,
        "mapping": mapping,
        "axes": axes,
    }
    with open(CALIB_FILE_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def find_dji_usb():
    for d in DEVICES:
        dev = usb.core.find(idVendor=DJI_VID, idProduct=d["pid"])
        if dev is not None:
            return dev, d
    return None, None


def run_interactive_calibration():
    dev, info = find_dji_usb()
    if dev is None:
        sys.exit("Tidak menemukan DJI RC 2 di USB (pastikan remote menyala & terhubung via USB-C).")
    try:
        if dev.is_kernel_driver_active(info["iface"]):
            dev.detach_kernel_driver(info["iface"])
    except Exception:
        pass
    usb.util.claim_interface(dev, info["iface"])

    print(f"=== Kalibrasi {info['name']} ===")
    print("Langkah 1/2: Lepaskan kedua stick & dial ke posisi TENGAH selama 2 detik...")
    seq = 1
    leftover = bytearray()
    centers = [[] for _ in range(6)]
    t_end = time.time() + 2.0
    while time.time() < t_end:
        seq = (seq + 1) & 0xFFFF
        dev.write(info["ep_out"], build_duml(10, 6, seq, 0x40, 0x06, 0xF5), timeout=100)
        try:
            raw = bytes(dev.read(info["ep_in"], 512, timeout=20))
            leftover += raw
            pkts, leftover = split_packets(leftover)
            leftover = bytearray(leftover)
            for p in pkts:
                if p[9] == 0x06 and p[10] == 0xF5 and len(p) >= 26:
                    vals = struct.unpack("<B6H", p[11:24])
                    for i in range(6):
                        centers[i].append(vals[1 + i])
        except Exception:
            pass

    cal_ctr = [int(round(sum(c) / max(1, len(c)))) for c in centers]
    cal_min = list(cal_ctr)
    cal_max = list(cal_ctr)

    print("Langkah 2/2: Putar KEDUA STICK dan KEDUA WHEEL (dial atas) mentok ke segala arah selama 8 detik!")
    t_end = time.time() + 8.0
    while time.time() < t_end:
        seq = (seq + 1) & 0xFFFF
        dev.write(info["ep_out"], build_duml(10, 6, seq, 0x40, 0x06, 0xF5), timeout=100)
        try:
            raw = bytes(dev.read(info["ep_in"], 512, timeout=20))
            leftover += raw
            pkts, leftover = split_packets(leftover)
            leftover = bytearray(leftover)
            for p in pkts:
                if p[9] == 0x06 and p[10] == 0xF5 and len(p) >= 26:
                    vals = struct.unpack("<B6H", p[11:24])
                    for i in range(6):
                        v = vals[1 + i]
                        if v < cal_min[i]:
                            cal_min[i] = v
                        if v > cal_max[i]:
                            cal_max[i] = v
                    rem = max(0.0, t_end - time.time())
                    sys.stdout.write(f"\rSisa waktu: {rem:4.1f}s | Span: {[cal_max[i]-cal_min[i] for i in range(6)]}   ")
                    sys.stdout.flush()
        except Exception:
            pass

    usb.util.release_interface(dev, info["iface"])
    save_calib(info, cal_min, cal_ctr, cal_max)
    print(f"\nKalibrasi berhasil disimpan ke {CALIB_FILE_PATH}!")


def run_axis_identification():
    """
    Walk the user through each physical input and report which raw channel
    actually moves. This is how you find out that - say - raw[3] is really the
    right stick's vertical axis on your unit, instead of guessing.
    """
    dev, info = find_dji_usb()
    if dev is None:
        sys.exit("Tidak menemukan DJI RC 2 di USB (pastikan remote menyala & terhubung via USB-C).")
    try:
        if dev.is_kernel_driver_active(info["iface"]):
            dev.detach_kernel_driver(info["iface"])
    except Exception:
        pass
    usb.util.claim_interface(dev, info["iface"])

    prompts = [
        ("RIGHT stick LEFT <- -> RIGHT", "Roll (aileron)"),
        ("RIGHT stick UP <- -> DOWN", "Pitch (elevator)"),
        ("LEFT stick UP <- -> DOWN", "Throttle"),
        ("LEFT stick LEFT <- -> RIGHT", "Yaw (rudder)"),
        ("LEFT top wheel (rotate fully)", "aux_left"),
        ("RIGHT top wheel (rotate fully)", "aux_right"),
    ]

    print("=" * 70)
    print("  AXIS IDENTIFICATION")
    print("  Follow each prompt. Move ONLY the input being asked about, then")
    print("  return it to center and wait for the result.")
    print("=" * 70)

    results = {}
    seq = 1
    leftover = bytearray()

    def poll_once():
        nonlocal seq, leftover
        seq = (seq + 1) & 0xFFFF
        dev.write(info["ep_out"], build_duml(10, 6, seq, 0x40, 0x06, 0xF5), timeout=100)
        raw = bytes(dev.read(info["ep_in"], 512, timeout=20))
        leftover += raw
        pkts, leftover = split_packets(leftover)
        leftover = bytearray(leftover)
        for p in pkts:
            if p[9] == 0x06 and p[10] == 0xF5 and len(p) >= 26:
                return list(struct.unpack("<B6H", p[11:24])[1:])
        return None

    def sample(seconds):
        """Record min/max per channel over a short window."""
        lo = [65535] * 6
        hi = [0] * 6
        t_end = time.time() + seconds
        while time.time() < t_end:
            vals = poll_once()
            if vals:
                for i in range(6):
                    lo[i] = min(lo[i], vals[i])
                    hi[i] = max(hi[i], vals[i])
        return [hi[i] - lo[i] for i in range(6)]

    # Establish a resting baseline so we can report absolute movement too.
    print("\nBaseline: lepaskan semua stick & wheel (3 detik)...")
    base_lo = [65535] * 6
    base_hi = [0] * 6
    t_end = time.time() + 3.0
    baseline = None
    while time.time() < t_end:
        vals = poll_once()
        if vals:
            baseline = vals
            for i in range(6):
                base_lo[i] = min(base_lo[i], vals[i])
                base_hi[i] = max(base_hi[i], vals[i])
    if baseline is None:
        usb.util.release_interface(dev, info["iface"])
        sys.exit("Gagal membaca data dari controller.")
    print(f"  Resting raw values: {baseline}")

    for prompt, role in prompts:
        input(f"\n>>> {prompt}  [tekan Enter kalau siap] ")
        print("    Merekan 3 detik... gerakkan sekarang!")
        spans = sample(3.0)
        ranked = sorted(range(6), key=lambda i: spans[i], reverse=True)
        best = ranked[0]
        results[role] = (best, spans[best])
        print(f"    -> channel yang paling bergerak: raw[{best}] (span {spans[best]})")
        print(f"       semua span: {spans}")

    usb.util.release_interface(dev, info["iface"])

    print("\n" + "=" * 70)
    print("  HASIL")
    print("=" * 70)
    for prompt, role in prompts:
        ch, span = results[role]
        print(f"  {role:<18} = raw[{ch}]   (span {span})")

    sources = {}
    for role, (ch, _) in results.items():
        sources.setdefault(ch, []).append(role)
    conflicts = {ch: roles for ch, roles in sources.items() if len(roles) > 1}
    if conflicts:
        print("\n  ⚠️  Ada konflik (satu channel dipakai beberapa role):")
        for ch, roles in conflicts.items():
            print(f"      raw[{ch}] <- {', '.join(roles)}")
        print("      Coba ulangi, dan pastikan hanya SATU input digerakkan tiap langkah.")
    else:
        print("\n  ✅ Tidak ada konflik — setiap input punya channel sendiri.")

    print("\n  Langkah selanjutnya:")
    print("   1. Buka src/calib.json")
    print("   2. Sesuaikan blok \"mapping\" dengan tabel di atas, mis.:")
    print('        "yaw": { "source": 3, "invert": false }')
    print("   3. Kalau arah stick masih terbalik, ubah \"invert\" jadi true.")
    print("   4. Jalankan ./scripts/install.sh lagi supaya plugin dibuild ulang.")


def main():
    if "--identify" in sys.argv or "--identify-axes" in sys.argv:
        run_axis_identification()
        return
    if "--calibrate" in sys.argv:
        run_interactive_calibration()
        return

    mm = open_shm()
    cal_min, cal_ctr, cal_max = load_calib()
    my_pid = os.getpid()

    print("======================================================================")
    print("  DJI RC 2 -> macOS Liftoff Bridge & Live Monitor")
    print("  Tekan Ctrl+C untuk berhenti. (Liftoff tetap bisa jalan mandiri!)")
    print("======================================================================")

    dev = None
    info = None
    seq = 0
    leftover = bytearray()
    packets_count = 0
    t_start = time.time()

    try:
        while True:
            # Check if Liftoff (another process) is already writing fresh USB data
            mm.seek(0)
            raw_shm = mm.read(STATE_STRUCT_SIZE)
            unpacked = struct.unpack(STATE_STRUCT_FMT, raw_shm)
            magic, ver, ts, writer_pid, connected = unpacked[:5]

            if magic == STATE_MAGIC and writer_pid != 0 and writer_pid != my_pid and (time.time() - ts) < 0.25:
                if dev is not None:
                    try:
                        usb.util.release_interface(dev, info["iface"])
                    except Exception:
                        pass
                    dev = None
                ail, ele, thr, rud, wl, wr = unpacked[5:11]
                raw_vals = unpacked[11:17]
                sys.stdout.write(
                    f"\r[Liftoff Active PID {writer_pid}] "
                    f"Lx(Yaw):{bar(rud,12)} {rud:+5.2f} | "
                    f"Ly(Thr):{bar(thr,12,bipolar=False)} {thr:5.2f} | "
                    f"Rx(Rol):{bar(ail,12)} {ail:+5.2f} | "
                    f"Ry(Pit):{bar(ele,12)} {ele:+5.2f} | "
                    f"WL:{wl:+5.2f} WR:{wr:+5.2f}  "
                )
                sys.stdout.flush()
                time.sleep(0.016)
                continue

            if dev is None:
                dev, info = find_dji_usb()
                if dev is None:
                    sys.stdout.write("\r[Menunggu DJI RC 2 di USB...] Pastikan remote menyala & terhubung.   ")
                    sys.stdout.flush()
                    time.sleep(0.5)
                    continue
                try:
                    if dev.is_kernel_driver_active(info["iface"]):
                        dev.detach_kernel_driver(info["iface"])
                except Exception:
                    pass
                try:
                    usb.util.claim_interface(dev, info["iface"])
                except usb.core.USBError:
                    # Interface claimed by Liftoff! Wait for shared memory updates
                    dev = None
                    time.sleep(0.1)
                    continue

                # Drain & query 0x06/0x38 hardware calibration
                while True:
                    try:
                        dev.read(info["ep_in"], 512, timeout=10)
                    except Exception:
                        break
                cal_min, cal_ctr, cal_max = load_calib()
                seq = (seq + 1) & 0xFFFF
                dev.write(info["ep_out"], build_duml(10, 6, seq, 0x40, 0x06, 0x38), timeout=50)
                try:
                    r38 = bytes(dev.read(info["ep_in"], 512, timeout=50))
                    pkts38, _ = split_packets(r38)
                    for p in pkts38:
                        if p[9] == 0x06 and p[10] == 0x38 and len(p) >= 50:
                            v38 = struct.unpack("<B18H", p[11:48])
                            for i in range(6):
                                mn, ct, mx = v38[1 + i * 3 : 1 + (i + 1) * 3]
                                if mn < ct < mx and (mx - mn) > 500:
                                    cal_min[i], cal_ctr[i], cal_max[i] = mn, ct, mx
                except Exception:
                    pass
                t_start = time.time()
                packets_count = 0

            seq = (seq + 1) & 0xFFFF
            try:
                dev.write(info["ep_out"], build_duml(10, 6, seq, 0x40, 0x06, 0xF5), timeout=50)
                data = bytes(dev.read(info["ep_in"], 512, timeout=15))
            except usb.core.USBError:
                try:
                    usb.util.release_interface(dev, info["iface"])
                except Exception:
                    pass
                dev = None
                continue

            leftover += data
            pkts, leftover = split_packets(leftover)
            leftover = bytearray(leftover)
            for p in pkts:
                if p[9] == 0x06 and p[10] == 0xF5 and len(p) >= 26:
                    vals = struct.unpack("<B6H", p[11:24])
                    raw = vals[1:7]
                    ail = scale_axis(raw[0], cal_min[0], cal_ctr[0], cal_max[0], 0.025)
                    ele = scale_axis(raw[1], cal_min[1], cal_ctr[1], cal_max[1], 0.025)
                    # Throttle self-centers on the DJI RC 2: released = 0.0, up = 1.0.
                    thr = scale_axis_unipolar(raw[2], cal_min[2], cal_ctr[2], cal_max[2])
                    rud = scale_axis(raw[3], cal_min[3], cal_ctr[3], cal_max[3], 0.025)
                    wl  = scale_axis(raw[4], cal_min[4], cal_ctr[4], cal_max[4], 0.030)
                    wr  = scale_axis(raw[5], cal_min[5], cal_ctr[5], cal_max[5], 0.030)

                    packed = struct.pack(
                        STATE_STRUCT_FMT,
                        STATE_MAGIC,
                        STATE_VERSION,
                        time.time(),
                        my_pid,
                        1,
                        ail, ele, thr, rud, wl, wr,
                        *raw,
                        *cal_min,
                        *cal_ctr,
                        *cal_max,
                    )
                    mm.seek(0)
                    mm.write(packed)
                    packets_count += 1

                    if packets_count % 8 == 0:
                        hz = packets_count / max(0.001, time.time() - t_start)
                        sys.stdout.write(
                            f"\r[{hz:5.1f} Hz] "
                            f"Lx(Yaw):{bar(rud,10)} {rud:+5.2f} | "
                            f"Ly(Thr):{bar(thr,10,bipolar=False)} {thr:5.2f} | "
                            f"Rx(Rol):{bar(ail,10)} {ail:+5.2f} | "
                            f"Ry(Pit):{bar(ele,10)} {ele:+5.2f} | "
                            f"WL:{wl:+5.2f} WR:{wr:+5.2f}  "
                        )
                        sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nMonitor dihentikan.")
    finally:
        if dev is not None:
            try:
                usb.util.release_interface(dev, info["iface"])
            except Exception:
                pass
        mm.close()


if __name__ == "__main__":
    main()
