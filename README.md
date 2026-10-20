# 🎮 Fly your DJI RC 2 in Liftoff on macOS

**If you have a DJI RC 2 sitting around and *Liftoff: FPV Drone Racing* on your Mac, this is the missing piece that lets them finally talk to each other.**

No ADB unlocking. No root or `sudo`. No extra dongles to buy. Plug in a USB-C cable, run one command, and go fly. 🚁

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Apple%20Silicon%20%7C%20Intel-blue?style=flat-square&logo=apple)]()
[![Python](https://img.shields.io/badge/python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#license)
[![Liftoff](https://img.shields.io/badge/game-Liftoff%20(FPV)-orange?style=flat-square)]()
[![DJI](https://img.shields.io/badge/hardware-DJI%20RC%20%7C%20RC%202-red?style=flat-square)]()

---

## ✨ Features

- 🎯 **~240 Hz polling** — direct DUML protocol polling over USB, no perceptible latency
- 🔌 **True plug-and-play** — works out of the box with the factory stick calibration stored in the controller's MCU
- 🧠 **Smart conflict avoidance** — automatically detects when Liftoff is polling USB itself and switches to a passive shared-memory monitor; both can run side by side, forever
- ⚙️ **Zero privileges** — no `sudo`, no root, no Android/ADB unlocking of the controller
- 🍎 **Universal binary** — the injected plugin is compiled for both Apple Silicon (`arm64`) and Intel (`x86_64`)
- 🛟 **Fully reversible** — the installer keeps a pristine backup of every file it touches; one command restores everything
- 🧰 **Interactive calibration tool** — on-screen wizard to fine-tune stick centers and ranges per-axis

## 📦 Supported Hardware

| Device | USB VID:PID | Status |
|:--|:--|:--:|
| **DJI RC 2** (rc331 — Mini 5 Pro / Air 3 / Mini 4 Pro) | `2ca3:1021` | ✅ Tested |
| **DJI RC** (rm330) | `2ca3:1023` | 🧪 Untested |

## 🧠 How It Works

```
┌──────────────┐   USB-C (DUML @ ~240 Hz)   ┌───────────────────────┐
│  DJI RC 2    │ ◄────────────────────────► │  src/dji_rc2_liftoff.py│
│  controller  │                            │  (Python bridge)      │
└──────────────┘                            └──────────┬────────────┘
                                                       │ shared memory
                                                       ▼ /tmp/dji_rc2_state.bin
                                            ┌───────────────────────┐
                                            │ Rewired_MacOS.bundle  │  ◄─ injected proxy
                                            │ (inside Liftoff.app)  │      plugin (Obj-C)
                                            └──────────┬────────────┘
                                                       ▼
                                            ┌───────────────────────┐
                                            │      Liftoff 🎮       │
                                            │   (FPV drone sim)     │
                                            └───────────────────────┘
```

1. **The plugin** (`scripts/install.sh`) compiles a small Objective-C proxy bundle (`src/rewired_dji_rc2.m`) that wraps the original `Rewired_MacOS.bundle` (Liftoff's controller-input plugin) and re-exports all of its symbols. The proxy is dropped into `Liftoff.app/Contents/PlugIns/`, where it transparently intercepts controller input.
2. **The bridge** (`src/dji_rc2_liftoff.py`) talks DUML — DJI's own serial protocol — straight to the controller over USB, decodes stick positions, applies calibration, and publishes them to a shared-memory file (`/tmp/dji_rc2_state.bin`).
3. **The plugin reads the shared memory** and feeds the values into Liftoff as a standard game controller. If you launch the plugin *inside* Liftoff first, the Python bridge notices and politely backs off into monitor-only mode — no USB contention, ever.

## 📋 Requirements

- macOS on **Apple Silicon** or **Intel**
- [Liftoff: FPV Drone Racing](https://store.steampowered.com/app/431710/Liftoff_FPV_Drone_Racing/) installed via **Steam**
- A **DJI RC 2** (or DJI RC) remote controller
- [Homebrew](https://brew.sh)
- Xcode Command Line Tools (`clang`, `install_name_tool`, `codesign`)
- Python 3.9+

## 🚀 Installation

Honestly, the whole thing takes about five minutes.

### 1. Install system dependencies

```bash
xcode-select --install          # if not already installed
brew install libusb python3
```

### 2. Clone the repository

```bash
git clone git@github.com:dzakwanf/dji-rc2-liftoff-plugin.git
cd dji-rc2-liftoff-plugin
```

### 3. Set up the Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. ✅ Locating Liftoff

Good news: the scripts no longer hardcode anyone's Steam library. By default they look in the standard location under your own home folder:

```
$HOME/Library/Application Support/Steam/steamapps/common/Liftoff/Liftoff.app
```

If Liftoff lives somewhere else (an external drive, a different library, a non-standard Steam install), just set `LIFTOFF_APP` when running the scripts:

```bash
LIFTOFF_APP="/Volumes/Games/Steam/steamapps/common/Liftoff/Liftoff.app" ./scripts/install.sh
```

The same variable works for `scripts/uninstall.sh`.

### 5. Install the plugin into Liftoff

```bash
./scripts/install.sh
```

This will:
1. Back up the original `Rewired_MacOS.bundle` → `Rewired_MacOS_orig.bundle`
2. Compile the universal (arm64 + x86_64) proxy plugin
3. Install it into `Liftoff.app/Contents/PlugIns/`
4. Patch `Rewired_Core.dll` to enable Apple's GameController backend
5. Code-sign everything (ad-hoc)

### 6. Launch Liftoff & plug in the controller

1. Start **Liftoff** from Steam
2. Connect the DJI RC 2 with a USB-C cable and power it on
3. Run the bridge in a terminal:

```bash
./scripts/run.sh
```

You should see live stick telemetry streaming:

```
[238.4 Hz] Lx(Yaw):──┼──█───────── +0.12 | Ly(Thr):──┼───────█── -0.31 | Rx(Rol):────█┼──────── +0.40 | Ry(Pit):──┼────█────── -0.05 | WL:+0.00 WR:+0.00
```

If Liftoff is already reading USB itself, the bridge automatically flips to passive monitor mode:

```
[Liftoff Active PID 4242] Lx(Yaw):──┼────█───── +0.05 | ...
```

🎉 That's it — your DJI RC 2 is now your Liftoff controller.

## 🎛️ Interactive Calibration (optional)

The bridge already fetches the factory stick calibration from the controller's MCU automatically. If you want to (re)calibrate manually — e.g. after a stick-center drift — run:

```bash
./scripts/run.sh --calibrate
```

You'll be guided through a two-step wizard:

1. **Step 1 (2 s):** release both sticks and wheels to their center position
2. **Step 2 (8 s):** rotate both sticks and both wheels to their extremes in every direction

Results are saved to `src/calib.json`.

## 🕹️ Throttle Behaviour

The DJI RC 2's left stick is **self-centering** — release it and it springs back to the middle. Most FPV radios instead have a friction/ratchet throttle that stays where you leave it, so this one difference trips up nearly everyone.

This project therefore treats the **released (centered) position as throttle 0**:

| Stick position | Throttle sent to Liftoff |
|:--|:--|
| Released / centered | `0.00` |
| Halfway up | `~0.50` |
| Fully up | `1.00` |
| Pulled down | `0.00` (clamped, never negative) |

So you push up to climb and let go to idle — no need to hold the stick down while flying, and no surprise spin-up when you release it.

This is controlled by `center` in the `mapping` block of `src/calib.json`:

```json
"throttle": { "source": 2, "invert": false, "center": false }
```

- `center: true` → bipolar, for self-centering sticks (`-1..1`, zero in the middle). Used for roll, pitch and yaw.
- `center: false` → unipolar with the center as zero (`0..1`). Used for throttle.

If you have fitted a ratchet/friction throttle to your radio and want the conventional "bottom = 0, top = 1" feel, flip that channel to the full range by giving it `"center": true` temporarily, or simply recalibrate with the stick held at the bottom.

## 🗑️ Uninstallation

```bash
./scripts/uninstall.sh
```

Restores the original `Rewired_MacOS.bundle` from backup and reverts the `Rewired_Core.dll` patch. Clean and complete.

## ❓ Troubleshooting

| Symptom | Fix |
|:--|:--|
| `Folder Liftoff PlugIns tidak ditemukan` | Liftoff isn't where the script expects it — see [step 4](#-locating-liftoff). |
| `[Waiting for DJI RC 2 on USB...]` | Make sure the controller is **powered on** and connected via a **data-capable** USB-C cable (some cables are charge-only). Check with `system_profiler SPUSBDataType`. |
| `LIBUSB_ERROR_ACCESS` | Another process (or Liftoff itself) is claiming the USB interface. Unplug/replug the controller, or quit Liftoff and retry. |
| `LIBUSB_ERROR_NOT_FOUND` | `libusb` isn't installed or isn't in the expected Homebrew path. Run `brew install libusb`. |
| Sticks drift / don't reach ±1.00 | Recalibrate: `./scripts/run.sh --calibrate` |
| Plugin not loaded by Liftoff | Verify code signatures: `codesign --verify --verbose=2` on the bundle. On some macOS versions you may need to allow it under **System Settings → Privacy & Security**. |
| Steam verifies game files & wipes the plugin | Just re-run `./scripts/install.sh` — it's idempotent. |

## 🗂️ Project Structure

```
dji-rc2-liftoff-plugin/
├── README.md
├── LICENSE
├── requirements.txt              # Python dependencies (pyusb)
├── src/                          # All source code
│   ├── dji_rc2_liftoff.py        # Python bridge: USB/DUML polling + shared memory + live monitor
│   ├── rewired_dji_rc2.m         # Objective-C proxy plugin injected into Liftoff
│   └── calib.json                # Stick calibration data (auto-generated)
├── scripts/                      # Entry points
│   ├── install.sh                # One-shot installer (backup → compile → install → patch → sign)
│   ├── uninstall.sh              # Full restore from backup
│   └── run.sh                    # Launches the bridge
├── build/                        # Local build artifacts (git-ignored, regenerated by install.sh)
└── .venv/                        # Python virtualenv (git-ignored)
```

## ⚠️ Disclaimer

This project reverse-engineers DJI's DUML protocol and patches game files, so a little honesty is due: use it at your own risk. It should not affect your DJI account, your drone, or your warranty — your controller is only ever *read* from, never written to — but a few sensible habits go a long way:

- Keep a backup of your game install
- Don't fly a real drone while the controller is in USB mode (seriously)
- This is a hobby project, and it's not affiliated with DJI, Steam, or the folks behind Liftoff

## 📜 Credits

Standing on the shoulders of:

- DUML protocol & CRC tables: [o-gs/dji-firmware-tools](https://github.com/o-gs/dji-firmware-tools)
- Input plugin being wrapped: **Rewired** by MadRobot Software (inside Liftoff)
- Built with [libusb](https://libusb.info/) and a lot of late-night terminal staring

## 📄 License

MIT — see [LICENSE](LICENSE).
