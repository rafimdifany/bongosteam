# bongo-steam - Work Plan

## TL;DR (For humans)

**What you'll get:** Aplikasi desktop Windows yang menampilkan avatar bongocat sebagai overlay livestream. Avatar bereaksi terhadap keyboard (tangan kiri), mouse click+scroll (tangan kanan), dan joystick/gamepad (mode terpisah dengan visual controller Xbox/DualShock 5 + highlight tombol yang ditekan). Window frameless, always-on-top, bisa di-drag. Dibuild jadi satu file `.exe`.

**Why this approach:** Python + PyQt5 + pynput + pygame adalah stack yang sama dengan referensi bongocat yang sudah terbukti. pygame hanya dipakai untuk input joystick (bukan rendering), jadi aman digabung dengan Qt. Semua input global di-handle pynput sehingga window tidak perlu click-through — streamer tinggal capture window-nya via OBS.

**What it will NOT do:**
- Tidak ada achievements, combo counter, sound effect, atau floating "+1" popup
- Tidak ada system tray icon atau auto-startup
- Bukan untuk macOS/Linux — Windows only
- Tidak bisa auto-detect mode — harus manual toggle

**Effort:** Medium (6-8 jam implementation)
**Risk:** Low — reference project sudah membuktikan arsitektur ini
**Decisions to sanity-check:** pynput perlu run as Admin di Windows untuk global hooks; joystick visual pakai placeholder yang bisa diganti nanti.

Your next move: `$start-work` untuk mulai implementasi. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, low risk. Python/PyQt5/pynput/pygame. 8 todos across 3 waves. Frameless overlay with 2 input modes. Standalone Windows .exe via PyInstaller.

## Scope
### Must have
- [x] Global keyboard hook — setiap keypress trigger tangan kiri
- [x] Global mouse hook — setiap click (L/M/R) + scroll trigger tangan kanan
- [x] Joystick polling — buttons + axes (deadzone 0.3) + hotplugging
- [x] Bongocat avatar 3 pose — idle, left paw slap, right paw slap
- [x] Idle breathing animation (sine wave, 16ms timer)
- [x] Mode Keyboard+Mouse — kiri=kbd, kanan=mouse
- [x] Mode Joystick — kedua tangan down, tampil visual controller, highlight tombol
- [x] Dua tipe controller visual — Xbox layout dan DualShock 5 layout
- [x] Manual mode toggle via shortcut (default Ctrl+Shift+M)
- [x] Frameless, always-on-top, draggable window
- [x] Skin system (folder-based, ganti gambar avatar)
- [x] INI config di %APPDATA%/bongo-steam.ini
- [x] PyInstaller build → single .exe (console-less)

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Achievements / unlockables
- Combo counter atau streak system
- Sound effects (WAV/OGG playback)
- Floating "+1" popup animations
- System tray icon atau minimize-to-tray
- Auto-startup with Windows
- Auto-update / network check
- Multi-monitor detection
- Window click-through (Qt.WindowTransparentForInput)
- pygame.display.init() — pygame ONLY for joystick subsystem
- Bloat abstractions — jangan bikin BaseManager, AbstractRenderer, dll kecuali benar-benar dibutuhkan

## Verification strategy
> Zero human intervention for automatable units; manual visual QA for input hardware.
- **Test decision:** tests-after + manual QA (user confirmed)
- **Automated:** pytest untuk config parser, controller_map JSON validator, mode state machine
- **Manual:** keyboard/mouse/joystick reaction, visual correctness, EXE build smoke test
- **Evidence:** .omo/evidence/task-<N>-bongo-steam.txt (screenshot filenames + timestamp)

## Execution strategy
### Parallel execution waves
Wave 1 (Foundation): Project skeleton, config, input hooks — zero visual dependency
Wave 2 (Visual): Avatar rendering, reaction system, idle animation
Wave 3 (Joystick): Controller visual + highlight, mode toggle, build

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | — | 3, 4 | 2 |
| 2 | — | 3, 4 | 1 |
| 3 | 1, 2 | 5, 6 | 4 |
| 4 | 1, 2 | 5, 6 | 3 |
| 5 | 3, 4 | 7 | 6 |
| 6 | 3, 4 | 7 | 5 |
| 7 | 5, 6 | 8 | — |
| 8 | 7 | — | — |

## Todos
> Implementation + Test = ONE todo. Never separate.

- [x] 1. Project skeleton + dependencies + config module
  **What to do:** Buat struktur project, requirements.txt, main.py entry point, dan config module (INI reader/writer dengan DEFAULT_CONFIG). Semua path pakai `resource_path()` helper untuk kompatibilitas PyInstaller.
  **Must NOT do:** Jangan pakai `pathlib.Path.home()` langsung — selalu lewat `resource_path()`. Jangan bikin config class yang terlalu abstrak.
  **Parallelization:** Wave 1 | Blocked by: — | Blocks: 3, 4
  **References:**
  - `bongo_cat/models/config.py:1-311` — DEFAULT_CONFIG pattern, INI read/write, type coercion
  - `bongo_cat/utils/resources.py:1-45` — resource_path() for bundled assets
  - `bongo_cat/__main__.py:1-6` — python -m entry
  - `bongo_cat/requirements.txt` — dependency list
  **Config keys (first pass):** mode (kbm|joystick), controller_type (xbox|ds5), skin (default), toggle_shortcut (ctrl+shift+m), window_x (-1=center), window_y (-1=center), launch_count (0)
  **Acceptance criteria (agent-executable):**
  - `python -c "from bongo_steam.models.config import ConfigManager; c = ConfigManager(); assert c.get('mode') == 'kbm'; c.set('mode', 'joystick'); assert c.get('mode') == 'joystick'"`
  - Config file created at correct OS path on first run
  - Type coercion works: `"true"` → `True`, `"50"` → `50`
  **QA scenarios:**
  - Happy: Set config value, save, restart app, value persists
  - Failure: Corrupted INI file → load defaults, warn in log
  - Evidence: `.omo/evidence/task-1-bongo-steam.txt`
  **Commit:** Y | `feat(skeleton): project structure, deps, config module`

- [x] 2. Input tracking — keyboard + mouse + joystick listeners
  **What to do:** Implement 3 listeners + InputManager coordinator. Keyboard & mouse pakai pynput (non-blocking, background thread). Joystick pakai pygame (background polling thread, 8ms interval). InputManager menerima callback dari masing-masing listener dan emit signal ke reaction system nanti.
  **Must NOT do:** Jangan panggil `pygame.display.init()` atau `pygame.display.set_mode()`. Hanya `pygame.init()` + `pygame.joystick.init()`. Jangan blokir main thread — semua listener di daemon thread. Jangan bikin event queue yang unbounded — max 100 events.
  **Parallelization:** Wave 1 | Blocked by: — | Blocks: 3, 4
  **References:**
  - `bongo_cat/input/input_manager.py:1-86` — coordinator pattern, signal emission
  - `bongo_cat/input/keyboard_listener.py:1-73` — pynput keyboard hook, active_keys set for debounce
  - `bongo_cat/input/mouse_listener.py:1-61` — pynput mouse hook, active_buttons set
  - `bongo_cat/input/controller_listener.py:1-226` — pygame joystick polling, axes deadzone, hat tracking
  - librarian research: pygame JOYDEVICEADDED/JOYDEVICEREMOVED events
  **Keyboard listener details:**
  - `pynput.keyboard.Listener(on_press=..., on_release=...)` — non-blocking
  - `on_press`: if key not in `active_keys`, add it, fire `on_input("keyboard", key_name)`
  - `on_release`: remove from `active_keys`
  - Suppress: False (jangan suppress input ke aplikasi lain)
  **Mouse listener details:**
  - `pynput.mouse.Listener(on_click=..., on_scroll=...)` — non-blocking
  - `on_click(x, y, button, pressed)`: if pressed and button not in active, fire `on_input("mouse_button", button_name)`
  - `on_scroll(x, y, dx, dy)`: fire `on_input("mouse_scroll", "up" if dy>0 else "down")` with 50ms debounce
  **Joystick listener details:**
  - Thread dengan loop: `pygame.event.pump()`, cek JOYDEVICEADDED/JOYDEVICEREMOVED
  - Poll: `joy.get_button(i)`, `joy.get_axis(i)` every 8ms (~125Hz)
  - Axes deadzone: 0.3, rising edge only (track previous state, fire on cross, re-arm when back in deadzone)
  - Button: fire on press only (not hold), track `pressed_buttons` set
  **Acceptance criteria (agent-executable):**
  - `python -c "from bongo_steam.input.keyboard_listener import KeyboardListener; kl = KeyboardListener(callback=lambda s,k: print(s,k)); kl.start(); import time; time.sleep(2); kl.stop()"` — prints key events when keys pressed
  - Same pattern for mouse and joystick listeners
  - `python -m pytest tests/ -k test_input` passes (mock callback verification)
  **QA scenarios:**
  - Happy: Press 'A' on keyboard → logs "keyboard a" in console. Click mouse → logs "mouse_button left". Move joystick axis past 0.3 → logs joystick axis event.
  - Failure: Start app without joystick → no crash, no pygame error. Connect joystick mid-run → JOYDEVICEADDED event fires. Disconnect → JOYDEVICEREMOVED fires.
  - Failure: Run without admin → pynput listener starts but warns in log about limited capture
  - Evidence: `.omo/evidence/task-2-bongo-steam.txt`
  **Commit:** Y | `feat(input): keyboard, mouse, joystick listeners with InputManager`

- [x] 3. Avatar renderer — Qt overlay window + bongocat poses + idle animation
  **What to do:** Buat `OverlayWindow` (QMainWindow, frameless, always-on-top, transparent background, draggable). Di dalamnya ada QLabel untuk menampilkan avatar image. Idle breathing animation pakai QTimer (16ms) dengan sine wave scale transform. Skin loading dari folder `assets/skins/<name>/`.
  **Must NOT do:** Jangan pakai `Qt.WindowTransparentForInput` atau `WA_TransparentForMouseEvents`. Jangan resize window dari user — fixed size based on image. Jangan pakai OpenGL/QGraphicsView kecuali performa jadi masalah — QLabel + QPixmap cukup.
  **Parallelization:** Wave 2 | Blocked by: 1, 2 | Blocks: 5, 6
  **References:**
  - `bongo_cat/ui/main_window.py:1-1752` — full window implementation (focus on: __init__ window flags, update_stretched_image, do_slap, idle animation timer)
  - `bongo_cat/models/skin_manager.py:1-201` — skin.json loading, image caching
  - `bongo_cat/animations/constants.py:1-344` — animation timing, stretch factors
  **Window specs:**
  - Flags: `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`
  - Attribute: `WA_TranslucentBackground` (true)
  - Size: ~200x200 (auto from image)
  - Default position: bottom-right corner of screen (`screen_geometry.bottomRight() - offset`)
  - Drag: override `mousePressEvent/mouseMoveEvent` pada window (atau dedicated drag handle)
  **Avatar rendering:**
  - 3 images per skin: `cat-rest.png` (idle), `cat-left.png` (left paw down), `cat-right.png` (right paw down)
  - Skin folder structure: `assets/skins/<name>/skin.json` + 3 PNGs
  - `skin.json`: `{"name": "...", "author": "...", "version": "...", "images": {"idle": "...", "left": "...", "right": "..."}}`
  - Default skin: copy from bongocat reference `skins/default/`
  **Idle animation:**
  - QTimer 16ms (~60fps)
  - Sine wave: `scale = 1.0 + math.sin(time.time() * 2.0) * 0.02` (gentle breathing, ±2%)
  - Apply via QPixmap.scaled() or QTransform
  **Acceptance criteria (agent-executable):**
  - `python -m bongo_steam` → window appears, frameless, on top, in bottom-right
  - Window is draggable (click avatar area, drag, window moves)
  - Breathing animation visible (screenshot at t=0 and t=2s differ slightly)
  - `SkinManager.load_skin("default")` loads 3 pixmaps successfully
  - Screenshot: `.omo/evidence/task-3-avatar-window.png`
  **QA scenarios:**
  - Happy: Run app → bongocat appears bottom-right, breathing. Drag to new position → stays. Close and reopen → remembers position.
  - Failure: Missing skin files → log error, show placeholder colored rectangle
  - Evidence: `.omo/evidence/task-3-bongo-steam.txt`
  **Commit:** Y | `feat(ui): overlay window with bongocat avatar and breathing animation`

- [x] 4. Reaction system — mode-based input → visual response
  **What to do:** Connect InputManager ke ReactionSystem. ReactionSystem punya state machine: MODE_KBM dan MODE_JOYSTICK. Setiap mode punya mapping: input mana trigger tangan kiri/kanan. ReactionSystem emit signal ke OverlayWindow untuk ganti pose + trigger animasi slap.
  **Must NOT do:** Jangan hardcode keyboard key mapping — simpan di config. Jangan trigger slap yang sama dua kali tanpa release event di antaranya. Jangan blokir main thread — semua heavy work di signal/slot async.
  **Parallelization:** Wave 2 | Blocked by: 1, 2 | Blocks: 5, 6
  **References:**
  - `bongo_cat/ui/main_window.py` — `trigger_slap` signal, `do_slap()` method, `on_input_manager_input()` slot
  - `bongo_cat/input/input_manager.py` — `on_input(source, detail)` → `trigger_slap.emit(source, detail)`
  **Mode KBM (keyboard + mouse):**
  - Keyboard → `left_paw_slap()` (left paw animates)
  - Mouse click/scroll → `right_paw_slap()` (right paw animates)
  - Both can fire simultaneously (independent paws)
  **Mode JOYSTICK:**
  - Any joystick button/axis → `both_paws_down()` (continuous pose, not slap)
  - Saat joystick mode: keyboard dan mouse input di-IGNORE (tidak trigger apa pun)
  **Slap animation timing:**
  - Pose swap: instant (ganti QPixmap)
  - Return to idle: after 150ms (QTimer.singleShot)
  - Minimum gap between slaps: 50ms (debounce per paw)
  **Controller button tracking (for highlight, implemented in Task 5):**
  - ReactionSystem menyimpan `pressed_joystick_buttons: Set[str]` yang selalu up-to-date
  - Emit `controller_state_changed(pressed_buttons)` signal untuk dikonsumsi ControllerVisual
  **Acceptance criteria (agent-executable):**
  - Unit test: `test_reaction_system.py` — mock input events, verify correct `left_paw_slap()` / `right_paw_slap()` / `both_paws_down()` called
  - Unit test: `test_mode_switch.py` — switch mode, verify input routing changes
  - Test: in KBM mode, keyboard event triggers only left paw, mouse triggers only right
  - Test: in JOYSTICK mode, keyboard/mouse events ignored
  **QA scenarios:**
  - Happy: Press keyboard → left paw slaps. Click mouse → right paw slaps. Both work simultaneously.
  - Happy: Scroll mouse wheel → right paw slaps per tick (50ms debounce)
  - Happy: Press joystick button → both paws down. Release → return to idle after 150ms.
  - Failure: Rapid key spam → paws debounced, no visual glitching
  - Evidence: `.omo/evidence/task-4-bongo-steam.txt`
  **Commit:** Y | `feat(reaction): mode-based reaction system with KBM and joystick modes`

- [x] 5. Controller visual — overlay image + button highlight + mode toggle UI
  **What to do:** Buat komponen ControllerVisual yang menampilkan gambar controller (Xbox atau DS5) dan highlight tombol yang sedang ditekan. Controller visual muncul DI BELAKANG avatar (sebagai background layer). Highlight pakai colored semi-transparent overlay rectangle di posisi tombol. Controller visual hanya muncul di joystick mode.
  **Must NOT do:** Jangan hardcode button positions — pakai JSON mapping file per tipe controller. Jangan overlay controller visual di atas avatar — harus di bawah. Jangan pakai gambar controller yang copyrighted — buat simple outline/silhouette placeholder.
  **Parallelization:** Wave 3 | Blocked by: 3, 4 | Blocks: 7
  **References:**
  - Librarian research: controller button layouts for Xbox and DualShock 5
  - `bongo_cat/input/controller_listener.py:1-226` — button/axis indices reference
  **Controller mapping JSON format** (`assets/controllers/xbox_map.json`):
  ```json
  {
    "image": "xbox.png",
    "buttons": {
      "0": {"label": "A", "x": 0.88, "y": 0.58, "w": 0.06, "h": 0.06, "color": "#00FF88"},
      "1": {"label": "B", "x": 0.94, "y": 0.52, "w": 0.06, "h": 0.06, "color": "#FF4444"},
      "2": {"label": "X", "x": 0.82, "y": 0.52, "w": 0.06, "h": 0.06, "color": "#4488FF"},
      "3": {"label": "Y", "x": 0.88, "y": 0.46, "w": 0.06, "h": 0.06, "color": "#FFAA00"},
      "4": {"label": "LB", "x": 0.12, "y": 0.15, "w": 0.10, "h": 0.04, "color": "#FFFFFF"},
      "5": {"label": "RB", "x": 0.78, "y": 0.15, "w": 0.10, "h": 0.04, "color": "#FFFFFF"},
      "7": {"label": "Start", "x": 0.50, "y": 0.40, "w": 0.04, "h": 0.02, "color": "#FFFFFF"}
    },
    "axes": {
      "0": {"label": "L-Stick H", "highlight": false},
      "1": {"label": "L-Stick V", "highlight": false},
      "2": {"label": "LT", "x": 0.10, "y": 0.18, "w": 0.06, "h": 0.04, "color": "#8888FF"},
      "3": {"label": "R-Stick H", "highlight": false},
      "4": {"label": "R-Stick V", "highlight": false},
      "5": {"label": "RT", "x": 0.84, "y": 0.18, "w": 0.06, "h": 0.04, "color": "#FF8888"}
    },
    "hats": {
      "0": {"up": {"x": 0.38, "y": 0.50, "w": 0.03, "h": 0.02}, "down": {"x": 0.38, "y": 0.56, "w": 0.03, "h": 0.02}, "left": {"x": 0.35, "y": 0.53, "w": 0.02, "h": 0.03}, "right": {"x": 0.41, "y": 0.53, "w": 0.02, "h": 0.03}}
    }
  }
  ```
  - Coordinates are relative (0.0–1.0) to controller image dimensions
  - Duplicate for ds5_map.json with DS5-specific positions
  **Controller visual rendering:**
  - Widget hierarchy: OverlayWindow → ControllerVisual (background, only in joystick mode) → AvatarLabel (foreground)
  - ControllerVisual shows: controller image + colored rectangles over pressed button regions
  - Highlight: QPainter.fillRect(color+150 alpha) over button region
  - When no buttons pressed: show controller image only, no highlights
  **Both-hands-down pose:**
  - In joystick mode, avatar shows special "hands down" pose (could be regular idle pose, or a separate "grip" image)
  - Initial implementation: use idle pose (simplest). Future: add `cat-grip.png` if desired.
  **Mode toggle UI:**
  - Keyboard shortcut: default Ctrl+Shift+M (from config `toggle_shortcut`)
  - On toggle: flip mode, show/hide controller visual, update avatar pose
  - Optional: small mode indicator label on window corner ("KBM" or "JOY")
  **Acceptance criteria (agent-executable):**
  - `python -c "from bongo_steam.models.controller_map import ControllerMap; m = ControllerMap('xbox'); assert '0' in m.buttons; assert m.buttons['0']['label'] == 'A'"`
  - Controller map JSON validation: `python -m pytest tests/ -k test_controller_map` — valid JSON, all required fields, coords 0-1
  - Visual: screenshot in joystick mode → controller image visible behind avatar
  - Visual: press joystick button → screenshot shows colored highlight on corresponding region
  **QA scenarios:**
  - Happy: Switch to joystick mode → controller appears, hands down pose. Press A → green highlight at A position. Release → highlight gone.
  - Happy: Switch to KBM mode → controller disappears, avatar in idle.
  - Happy: Ctrl+Shift+M toggles mode correctly.
  - Failure: Corrupted map JSON → fallback to Xbox default, log warning
  - Failure: Controller image missing → show blank background with button position debug rectangles
  - Evidence: `.omo/evidence/task-5-bongo-steam.txt`, screenshots
  **Commit:** Y | `feat(ui): controller visual overlay with button highlights and mode toggle`

- [x] 6. Skin system — load custom avatar images from folder
  **What to do:** Implementasi SkinManager yang load skin dari folder `assets/skins/<name>/`. Support ganti skin via config key `skin`. Validasi skin.json structure. Cache pixmaps. Reload on skin change.
  **Must NOT do:** Jangan support hot-reload (harus restart untuk ganti skin — keep simple). Jangan support image formats selain PNG.
  **Parallelization:** Wave 3 | Blocked by: 3, 4 | Blocks: 7
  **References:**
  - `bongo_cat/models/skin_manager.py:1-201` — full skin loading implementation
  - `bongo_cat/skins/default/skin.json` — skin manifest format
  **Implementation:**
  ```python
  class SkinManager:
      def __init__(self, config: ConfigManager):
          self.config = config
          self.skins_dir = resource_path("assets/skins")
          self.current_skin = None
          self.pixmaps: dict[str, QPixmap] = {}  # {"idle": ..., "left": ..., "right": ...}
      
      def load_skin(self, skin_name: str = None):
          folder = self.skins_dir / (skin_name or self.config.get("skin"))
          manifest = json.loads((folder / "skin.json").read_text())
          for pose_key, filename in manifest["images"].items():
              self.pixmaps[pose_key] = QPixmap(str(folder / filename))
          self.current_skin = manifest["name"]
      
      def get_pixmap(self, pose: str) -> QPixmap:
          return self.pixmaps.get(pose)
      
      def list_skins(self) -> list[str]:
          return [d.name for d in self.skins_dir.iterdir() if d.is_dir() and (d / "skin.json").exists()]
  ```
  **Acceptance criteria (agent-executable):**
  - `python -c "from bongo_steam.models.skin_manager import SkinManager; m = SkinManager(config); m.load_skin('default'); assert m.get_pixmap('idle') is not None; assert m.get_pixmap('left') is not None; assert m.get_pixmap('right') is not None"`
  - `python -m pytest tests/ -k test_skin_manager` — valid skin loads, missing image raises clear error, invalid JSON handled gracefully
  **QA scenarios:**
  - Happy: Change config `skin = "neon"`, restart → avatar changes to neon skin
  - Failure: Skin folder missing `cat-right.png` → log error, use default skin as fallback
  - Evidence: `.omo/evidence/task-6-bongo-steam.txt`
  **Commit:** Y | `feat(skin): skin loading system with folder-based skins`

- [x] 7. Integration — wire all components + main.py + assets + config persistence
  **What to do:** Hubungkan semua komponen di `main.py`. Init: Config → SkinManager → OverlayWindow → InputManager → ReactionSystem → ControllerVisual. Setup signal/slot connections. Handle window close → save config. Handle joystick disconnect → auto-switch mode. Copy default assets dari referensi bongocat (skin images, placeholder controller images).
  **Must NOT do:** Jangan ada circular imports. Jangan init pygame sebelum QApplication. Jangan lupa cleanup (stop listeners, pygame.quit) on exit.
  **Parallelization:** Wave 3 | Blocked by: 5, 6 | Blocks: 8
  **References:**
  - `bongo_cat/main.py:1-44` — full init sequence
  - All component files from tasks 1-6
  **main.py structure:**
  ```python
  import sys, os, atexit
  os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=0"
  
  from PyQt5.QtWidgets import QApplication
  from PyQt5.QtCore import Qt
  
  from bongo_steam.models.config import ConfigManager
  from bongo_steam.models.skin_manager import SkinManager
  from bongo_steam.models.controller_map import ControllerMap
  from bongo_steam.ui.overlay_window import OverlayWindow
  from bongo_steam.ui.controller_visual import ControllerVisual
  from bongo_steam.input.input_manager import InputManager
  from bongo_steam.reaction.reaction_system import ReactionSystem
  
  def main():
      app = QApplication(sys.argv)
      app.setQuitOnLastWindowClosed(True)
      
      config = ConfigManager()
      skin_manager = SkinManager(config)
      skin_manager.load_skin(config.get("skin", "default"))
      
      controller_map_xbox = ControllerMap("xbox")
      controller_map_ds5 = ControllerMap("ds5")
      
      window = OverlayWindow(config, skin_manager)
      controller_visual = ControllerVisual(window, controller_map_xbox, controller_map_ds5, config)
      
      input_manager = InputManager()
      reaction_system = ReactionSystem(config, window, controller_visual)
      
      input_manager.on_input.connect(reaction_system.handle_input)
      
      controller_visual.hide()  # Start in KBM mode
      reaction_system.set_mode("kbm")
      
      atexit.register(cleanup, input_manager)
      
      window.show()
      sys.exit(app.exec_())
  
  def cleanup(input_manager):
      input_manager.stop_all()
      pygame.quit()
  ```
  **Asset setup:**
  - Copy `skins/default/*` dari referensi bongocat ke `assets/skins/default/`
  - Buat placeholder controller images: simple SVG/PNG outline siluet Xbox dan DS5
  - Buat `xbox_map.json` dan `ds5_map.json` dengan button positions
  **Config persistence:**
  - On window close (`closeEvent`): `config.set("window_x", self.x()); config.set("window_y", self.y()); config.save()`
  - On mode toggle: `config.set("mode", new_mode); config.save()`
  - Graceful: simpan setiap kali ada perubahan (debounced 500ms) atau saat close
  **Joystick disconnect handling:**
  - Listener detects JOYDEVICEREMOVED → emit signal
  - ReactionSystem receives → if in joystick mode, auto-switch to KBM mode + show transient "Controller disconnected" toast
  **Acceptance criteria (agent-executable):**
  - `python -m bongo_steam` → app starts, window visible, no crash
  - Window position restored from config on 2nd launch
  - Mode toggle via Ctrl+Shift+M works end-to-end
  - Close window → config saved, process exits clean (no zombie threads)
  - `python -m pytest tests/ -k test_integration` — smoke test all component init
  **QA scenarios:**
  - Happy: Full flow — start app, press keys (avatar reacts), toggle to joystick (controller appears, hands down), press joystick buttons (highlights), disconnect joystick (auto-switch back to KBM), close (position saved)
  - Failure: Start without admin → app runs, input hooks work (or warn if limited)
  - Failure: Missing controller image → json map still works, show debug rectangles
  - Evidence: `.omo/evidence/task-7-bongo-steam.txt`
  **Commit:** Y | `feat(integration): wire all components, main entry, assets, config persistence`

- [x] 8. Build — PyInstaller Windows EXE + smoke test
  **What to do:** Buat PyInstaller spec file, build script, dan smoke test. Hasilkan single `.exe` file yang bisa dijalankan tanpa Python terinstall. Test di environment Windows bersih.
  **Must NOT do:** Jangan bundle Python interpreter — pakai PyInstaller one-file mode. Jangan lupa sertakan hidden imports (PyQt5, pynput, pygame). Jangan sign EXE (belum perlu).
  **Parallelization:** Wave 3 | Blocked by: 7 | Blocks: —
  **References:**
  - `bongo_cat.spec:1-end` — full PyInstaller spec with hidden imports and data files
  - `requirements.txt:1-6` — exact dependency versions
  **bongo_steam.spec:**
  ```python
  # -*- mode: python -*-
  import sys, os
  from PyInstaller.utils.hooks import collect_data_files
  
  a = Analysis(
      ['bongo_steam/main.py'],
      pathex=[],
      binaries=[],
      datas=[
          ('assets/skins', 'assets/skins'),
          ('assets/controllers', 'assets/controllers'),
      ],
      hiddenimports=[
          'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
          'pynput.keyboard._win32', 'pynput.mouse._win32',
          'pygame', 'pygame.joystick',
      ],
      hookspath=[],
      runtime_hooks=[],
      excludes=['tkinter'],
  )
  
  pyz = PYZ(a.pure, a.zipped_data)
  
  exe = EXE(
      pyz,
      a.scripts,
      a.binaries,
      a.zipfiles,
      a.datas,
      name='BongoSteam',
      debug=False,
      bootloader_ignore_signals=False,
      strip=False,
      upx=True,
      console=False,  # NO console window
      icon='assets/bongo-steam.ico',
      uac_admin=True,  # Request admin for global hooks
  )
  ```
  **Build script** (`build.bat`):
  ```bat
  @echo off
  pip install -r requirements.txt pyinstaller
  pyinstaller --clean --noconfirm bongo_steam.spec
  echo Build complete: dist/BongoSteam.exe
  ```
  **Smoke test checklist (MANUAL QA):**
  1. Copy `dist/BongoSteam.exe` ke folder kosong
  2. Double-click → window muncul (frameless, bottom-right)
  3. Press keyboard → left paw reacts
  4. Click mouse → right paw reacts
  5. Ctrl+Shift+M → switch to joystick mode → controller visual appears
  6. Connect joystick → detected, press button → highlight
  7. Disconnect joystick → auto-switch back to KBM
  8. Close window → reopen → position remembered
  9. Check Task Manager: no console window, single process, <100MB RAM
  **Acceptance criteria (agent-executable):**
  - `pyinstaller --clean --noconfirm bongo_steam.spec` exits 0
  - `dist/BongoSteam.exe` exists and is > 20MB (bundled Python + Qt)
  - `python -c "import zipfile; z = zipfile.ZipFile('dist/BongoSteam.exe'); print('OK')"` fails — it's a PE executable, not zip
  **QA scenarios:**
  - Happy: Build completes, EXE runs on clean Windows machine
  - Failure: Missing DLL → documented in README (install VC++ redist)
  - Evidence: `.omo/evidence/task-8-bongo-steam.txt` (build log + smoke test results)
  **Commit:** Y | `build: pyinstaller spec and build script for Windows EXE`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [x] F1. Plan compliance audit — verify every todo completed, every acceptance criteria met, no scope creep
- [x] F2. Code quality review — check: no `pygame.display.init()`, no hardcoded paths, all config keys documented, resource_path() used everywhere
- [x] F3. Real manual QA — end-to-end run on Windows 10/11 with keyboard, mouse, Xbox controller, DS5 controller
- [x] F4. Scope fidelity — verify IN scope items all present, OUT scope items all absent (no achievements/combo/sound code)

## Commit strategy
- 8 atomic commits, one per todo
- Commit format: `type(scope): description` (conventional commits)
- Each commit = implementation + test for one component
- Final commit tagged `v0.1.0`

## Success criteria
1. BongoSteam.exe runs on Windows 10/11 without Python installed
2. Keyboard presses trigger left paw reaction
3. Mouse clicks + scroll trigger right paw reaction  
4. Ctrl+Shift+M switches between KBM and Joystick mode
5. Joystick mode shows controller visual with highlighted pressed buttons
6. Joystick hotplugging works (connect/disconnect detected)
7. Window position persists across restarts
8. Window is frameless, always-on-top, draggable
9. Works with OBS window capture for streaming

(End of plan)
