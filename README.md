<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bongo-steam-banner-dark.png">
    <img alt="BongoSteam" src="assets/bongo-steam-banner.png" width="600">
  </picture>
</p>

<p align="center">
  <strong>Windows Desktop Livestream Avatar Overlay</strong><br>
  Bongocat reacts to your keyboard, mouse, and controller — perfect for OBS streams.
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#building">Building</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#architecture">Architecture</a>
</p>

---

## 🎮 What is BongoSteam?

BongoSteam is a **frameless, always-on-top avatar overlay** for Windows livestreams. Your bongocat avatar sits in the corner of your screen and reacts to every input — keyboard taps make the left paw slap, mouse clicks make the right paw slap, and controller input brings both paws down with a visual controller overlay.

Capture it with **OBS window capture** and your viewers see a cute, reactive companion while you play.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| ⌨️ **Keyboard** | Any keypress → left paw slap |
| 🖱️ **Mouse** | Click or scroll → right paw slap |
| 🎮 **Joystick** | Any button press → both paws down + controller visual |
| 🔄 **Mode Toggle** | `Ctrl+Shift+M` switches between KBM and Joystick modes |
| 🎨 **Skins** | Folder-based skin system — drop in your own artwork |
| 🖼️ **Frameless** | Always-on-top, transparent background, draggable window |
| 💾 **Position Memory** | Window position persists across restarts |
| 🫁 **Idle Animation** | Gentle breathing effect when no input is active |
| 📦 **Single EXE** | Build to one portable `.exe` with PyInstaller |

### Controller Support

| Controller | Visual Overlay | Button Highlights |
|------------|---------------|-------------------|
| Xbox | ✅ Full | ✅ Yes |
| DualShock 5 | ✅ Full | ✅ Yes |

---

## 🚀 Quick Start

### Prerequisites

- **Windows 10/11**
- **Run as Administrator** (required for global input hooks)
- Python 3.11+ (development only)

### Run from Source

```bash
git clone https://github.com/rafimdifany/bongosteam.git
cd bongosteam
pip install -r requirements.txt
python -m bongo_steam
```

### Run the EXE

Download `BongoSteam.exe` from [Releases](https://github.com/rafimdifany/bongosteam/releases). **Right-click → Run as Administrator**.

---

## ⌨️ Usage

**KBM Mode (default):** ANY KEYBOARD KEY → left paw slaps | MOUSE CLICK/SCROLL → right paw slaps

**Joystick Mode (Ctrl+Shift+M):** ANY CONTROLLER BUTTON → both paws down. Controller visual shows pressed buttons highlighted. Disconnect controller → auto-switches back to KBM.

**Window:** Drag anywhere on screen. Position saved automatically on close.

---

## 🔨 Building

```cmd
pip install -r requirements.txt pyinstaller
build.bat
```
Output: `dist/BongoSteam.exe`

---

## ⚙️ Configuration

`bongo_steam.ini` created on first run:

| Key | Values | Default |
|-----|--------|---------|
| `mode` | `kbm`, `controller` | `kbm` |
| `skin` | any folder in `assets/skins/` | `default` |
| `toggle_shortcut` | any modifier+key combo | `ctrl+shift+m` |
| `opacity` | `0.0` – `1.0` | `0.95` |
| `scale` | any positive float | `1.0` |

---

## 🎨 Custom Skins

```
assets/skins/my-skin/
├── skin.json          # { "name": "My Skin", "author": "You" }
├── idle.png           # neutral pose
├── left.png           # left paw slap
├── right.png          # right paw slap
└── both.png           # both paws down
```

Set `skin = my-skin` in config. App hot-reloads on mode toggle.

---

## 🏗️ Architecture

```
bongo_steam/
├── main.py                    # Entry point
├── models/                    # Config, Skin Manager, Controller Maps
├── input/                     # Keyboard, Mouse, Joystick listeners
├── reaction/                  # Input → Reaction state machine
└── ui/                        # Overlay Window, Controller Visual
```

### Thread Safety

All input listeners run in **background threads**. UI updates route through **`pyqtSignal`** to ensure all Qt widget operations stay on the main thread.

### Tech Stack

| Component | Library |
|-----------|---------|
| GUI | PyQt5 5.15 |
| Input Hooks | pynput 1.7 |
| Joystick | pygame 2.6+ |
| Build | PyInstaller |
| Tests | pytest (175 tests) |

---

## 🧪 Testing

```bash
pytest tests/
# ============================= 175 passed in 3.70s =============================
```

| Suite | Tests |
|-------|-------|
| Config | 6 |
| Input | 31 |
| Reaction | 39 |
| Overlay | 83 |
| Controller | 23 |
| Integration | 16 |

---

## ❓ Troubleshooting

- **"Input not detected"** → Run as Administrator
- **"Window not visible"** → Delete `bongo_steam.ini` to reset position
- **"Controller not detected"** → Connect before launching, press any button
- **"EXE won't run"** → Install [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## 📄 License

MIT

---

## 🙏 Acknowledgments

Original bongocat concept by StrayRogue and the streamer community. Built with PyQt5, pynput, and pygame.
