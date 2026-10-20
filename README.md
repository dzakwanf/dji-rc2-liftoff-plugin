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

- 🎯 **~200 Hz polling** — direct DUML protocol polling over USB, no perceptible latency
- 🔌 **True plug-and-play** — works out of the box with the factory stick calibration stored in the controller's MCU
- 🧠 **Smart conflict avoidance** — automatically detects when Liftoff is polling USB itself and switches to a passive shared-memory monitor; both can run side by side, forever
- ⚙️ **Zero privileges** — no `sudo`, no root, no Android/ADB unlocking of the controller
- 🍎 **Universal binary** — the injected plugin is compiled for both Apple Silicon (`arm64`) and Intel (`x86_64`)
- 🛟 **Fully reversible** — the installer keeps a pristine backup of every file it touches; one command restores everything
- 🧰 **Interactive calibration** — a guided wizard that measures the travel *and* the direction of every stick, so the axes come out the right way round
- 🩺 **Diagnostic toolkit** — a set of small scripts that measure what the controller actually reports, for when something does not add up

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

### Control mapping

The controller presents itself to Liftoff as a gamepad with a familiar layout:

| Physical control | Gamepad axis | Monitor label |
|:--|:--|:--|
| Left stick, horizontal | `leftThumbstick.xAxis` | `Lx(Yaw)` |
| Left stick, vertical | `leftThumbstick.yAxis` | `Ly(Thr)` |
| Right stick, horizontal | `rightThumbstick.xAxis` | `Rx(Rol)` |
| Right stick, vertical | `rightThumbstick.yAxis` | `Ry(Pit)` |
| Top-left wheel | `leftTrigger` | `WL` |
| Top-right wheel | `rightTrigger` | `WR` |

Every axis runs from `-1.00` to `+1.00` with zero in the middle, so the full travel of the stick is used in both directions.

## 📋 Requirements

- macOS on **Apple Silicon** or **Intel**
- [Liftoff: FPV Drone Racing](https://store.steampowered.com/app/410340/Liftoff_FPV_Drone_Racing/) installed via **Steam**
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

1. Start **Liftoff from Steam** — press Play in the Steam library, or run:

   ```bash
   open "steam://rungameid/410340"
   ```

   ⚠️ **Launch it through Steam, not with `open -a Liftoff.app`.** Liftoff needs Steam to hand it the app ID, and without it Steamworks fails to initialise and the game stops before it ever loads the input system. You will see `Steamworks is not initialized` in the log and the controller will not be picked up at all, no matter how the plugin is installed.

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

You'll be guided through a three-step wizard:

1. **Step 1 (2 s):** release both sticks and wheels to their center position
2. **Step 2 (8 s):** rotate both sticks and both wheels to their extremes in every direction
3. **Step 3:** hold each stick at a known extreme so the wizard can tell which end of a channel is the top of the stick

Step 3 is what keeps the axes from coming out backwards. A min/max sweep on its own cannot tell you whether the top of the stick is the larger or the smaller number, so the wizard asks you to hold each direction and records it.

Results are saved to `src/calib.json`.

### Checking the channel order

If a stick shows up under the wrong label — pushing the right stick sideways moves the value the plugin calls yaw, for instance — the controller's firmware has ordered the channels differently than expected. `./scripts/run.sh --identify` walks you through each input and reports which raw channel it actually moves, along with a `mapping` block ready to paste into `src/calib.json`.

### The `mapping` block

`src/calib.json` has two parts. `axes` holds the measured range for each channel, and `mapping` says which channel drives which role and in which direction:

```json
"mapping": {
  "roll":     { "source": 0, "invert": false, "center": true },
  "pitch":    { "source": 1, "invert": false, "center": true },
  "throttle": { "source": 2, "invert": false, "center": true },
  "yaw":      { "source": 3, "invert": false, "center": true }
}
```

- `source` — which raw channel the role reads.
- `invert` — flips the sign, for when a role still feels the wrong way round.
- `center` — `true` for a stick that rests in the middle (bipolar, `-1..1`), `false` for a lever that rests at one end.

The expected direction of each axis is recorded in the file itself, under `_direction`:

```json
"_direction": {
  "roll":     "kanan = positif, kiri = negatif",
  "pitch":    "atas = positif, bawah = negatif",
  "throttle": "atas = +1.0, netral = 0.0, bawah = -1.0",
  "yaw":      "kanan = positif, kiri = negatif"
}
```

## 🕹️ Throttle Behaviour

The DJI RC 2's left stick is **self-centering** — release it and it springs back to the middle. Most FPV radios instead have a friction/ratchet throttle that stays where you leave it, so this one difference trips up nearly everyone.

The stick is still scaled **bipolar**, the same as roll, pitch and yaw, so the whole travel is used and the axis can reach its low end:

| Stick position | Throttle sent to Liftoff |
|:--|:--|
| Fully down | `-1.00` |
| Released / centered | `0.00` |
| Halfway up | `~0.50` |
| Fully up | `+1.00` |

That gives you a real negative value at the bottom, which matters: Liftoff arms on **throttle low plus yaw**, and a throttle that only ever reports `0..1` sits in the middle of the axis where that gesture can never be satisfied. With this mapping you pull the left stick down, hold it there, and move the yaw to arm.

Because the stick springs back, you have to **hold** it down while you yaw rather than just resting it there.

If you have fitted a ratchet/friction throttle to your radio and would rather have the conventional "bottom = 0, top = 1" feel, set that channel to `"center": false` in the `mapping` block of `src/calib.json` and it is scaled as a lever that rests at its low end instead.

The `center` flag in the `mapping` block chooses between the two:

- `center: true` → bipolar, zero in the middle (`-1..1`). Used for every axis here, throttle included.
- `center: false` → a lever that rests at its low end, scaled `-1..1` with the resting position at `-1`.

## 🗑️ Uninstallation

```bash
./scripts/uninstall.sh
```

Restores the original `Rewired_MacOS.bundle` from backup and reverts the `Rewired_Core.dll` patch. Clean and complete.

## ❓ Troubleshooting

| Symptom | Fix |
|:--|:--|
| `Folder Liftoff PlugIns tidak ditemukan` | Liftoff isn't where the script expects it — see [step 4](#-locating-liftoff). |
| **Controller not detected at all, no telemetry** | Launch Liftoff **through Steam** (`open "steam://rungameid/410340"`), not with `open -a`. Without Steam the game fails to initialise and never loads the input system. Check `~/Library/Logs/LuGus Studios/Liftoff/Player.log` for `Steamworks is not initialized`. |
| `[Waiting for DJI RC 2 on USB...]` | Make sure the controller is **powered on** and connected via a **data-capable** USB-C cable (some cables are charge-only). Check with `system_profiler SPUSBDataType`. |
| `LIBUSB_ERROR_ACCESS` | Another process (or Liftoff itself) is claiming the USB interface. Unplug/replug the controller, or quit Liftoff and retry. |
| `LIBUSB_ERROR_NOT_FOUND` | `libusb` isn't installed or isn't in the expected Homebrew path. Run `brew install libusb`. |
| Controller shows in System Information but `libusb` sees nothing | macOS is gating the device. Unplug it, wait a few seconds, and plug it straight into a USB-C port on the machine rather than through a hub. `scripts/check_usb.py` compares what macOS sees against what `libusb` can open. |
| Sticks drift / don't reach ±1.00 | Recalibrate: `./scripts/run.sh --calibrate` |
| Can't arm the drone | The throttle must be able to reach its low end. Confirm `Ly(Thr)` goes negative when you pull the left stick down; if it does not, recalibrate so the throttle is scaled bipolar. |
| Plugin not loaded by Liftoff | Verify code signatures: `codesign --verify --verbose=2` on the bundle. On some macOS versions you may need to allow it under **System Settings → Privacy & Security**. |
| Steam verifies game files & wipes the plugin | Just re-run `./scripts/install.sh` — it's idempotent. |

## 🩺 Diagnostic Toolkit

Sometimes the numbers do not add up and it is hard to tell whether the problem is the cable, macOS, the plugin, or the calibration. These small scripts each answer one question by measuring the controller directly.

Most of them read the shared-memory file, so start the bridge first in one terminal and run the script in another:

```bash
./scripts/run.sh          # terminal 1
.venv/bin/python scripts/diagnose_axes.py   # terminal 2
```

| Script | What it answers |
|:--|:--|
| `scripts/check_usb.py` | Is the controller reachable? Compares what macOS enumerates against what `libusb` can actually open. A controller that shows up in System Information but is invisible to `libusb` is a permissions problem, not a cable one. |
| `scripts/diagnose_axes.py` | Which way does each stick really read? Sweeps every channel and reports the direction the device actually produces. |
| `scripts/diagnose_throttle.py` | Which way does the throttle read? Focused check on the left stick, and it prints a `calib.json` block you can paste straight in. |
| `scripts/identify_channels.py` | Which raw channel belongs to which physical input? Records all six channels at once while you hold each input in turn. |
| `scripts/record_all.py` | Records all six channels and reports the resulting mapping, with a countdown so you do not have to race a prompt. |
| `scripts/record_sticks.py` | Prints what the controller reports for each input as you move it. |

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
│   ├── run.sh                    # Launches the bridge (also --calibrate / --identify)
│   └── *.py                      # Diagnostic helpers, see the toolkit above
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
