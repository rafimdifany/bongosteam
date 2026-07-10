# Bongo-Steam Project Learnings

## Input Tracking System (Task 2)

### Joystick Hotplugging Implementation

**Pygame Event Types:**
- `JOYDEVICEADDED` (event type 1536): Fired when a new joystick is connected
- `JOYDEVICEREMOVED` (event type 1537): Fired when a joystick is disconnected
- Available since pygame 2.0+

**Implementation Details:**
1. **Instance ID Tracking:**
   - Each joystick has a unique `instance_id` that persists across the connection
   - Use `joystick.get_instance_id()` to track joysticks (not device index)
   - Device index can change when joysticks are added/removed, but instance_id is stable

2. **Joystick Initialization:**
   - Call `pygame.joystick.init()` ONLY - never `pygame.display.init()`
   - This allows headless operation without a display
   - Joystick subsystem works independently of display subsystem

3. **Polling Thread:**
   - 8ms interval (~125Hz) for responsive input detection
   - Daemon thread to avoid blocking application shutdown
   - Event processing + fallback polling for robustness

4. **Button Detection:**
   - Rising edge detection: fire callback only on initial press, not hold
   - Track `pressed_buttons` set per joystick to prevent duplicate triggers
   - Button naming: `joy{index}_button{num}` (e.g., `joy0_button0`)

5. **Axis Handling:**
   - Deadzone: 0.3 (30% of range) to ignore small movements/noise
   - Rising edge detection: fire only when crossing deadzone threshold
   - Re-arm: remove from active set when value returns to deadzone
   - Axis naming: `joy{index}_axis{num}` (e.g., `joy0_axis0`)

**Windows Considerations:**
- pynput requires administrator privileges for global keyboard/mouse hooks
- Document this in user-facing documentation
- Consider adding fallback mode with reduced privileges

### Mouse Scroll Debounce

**Implementation:**
- 50ms minimum interval between scroll callbacks
- Track `last_scroll_time` and check elapsed time before firing
- Prevents callback spam from high-resolution scroll wheels
- Direction detection: positive `dy` = up, negative `dy` = down

### Keyboard Key Name Conversion

**Approach:**
- `keyboard.Key` enum → use `.name` property (e.g., "space", "shift")
- `keyboard.KeyCode` with char → use `.char.lower()` for consistency
- `keyboard.KeyCode` with virtual key → fallback to `vk_{code}`
- All keys normalized to lowercase for consistent matching

### Testing Strategy

**Mock Considerations:**
- pynput listeners are difficult to mock directly
- Focus on testing internal logic (debounce, key conversion, etc.)
- Integration tests verify threading and lifecycle management
- Use patches for pygame availability checks

**Threading Tests:**
- Allow 100-200ms for threads to start/stop
- Use daemon threads to prevent test hangs
- Clean shutdown verification via `is_running()` checks

## Reaction System (Task 4)

### Mode-Based Input Routing

**State Machine Design:**
- Two modes: `MODE_KBM` (keyboard/mouse) and `MODE_JOYSTICK` (controller)
- Mode stored as Enum for type safety and easy comparison
- Mode switching via `set_mode()` with case-insensitive input
- Invalid modes fall back to KBM (sensible default)

**Input Routing Rules:**
1. **KBM Mode:**
   - `keyboard` → `left_paw_slap()`
   - `mouse_button` or `mouse_scroll` → `right_paw_slap()`
   - Joystick input is ignored
   - Left and right paws are independent (can trigger simultaneously)

2. **JOYSTICK Mode:**
   - Any `joystick` input (button or axis) → `both_paws_down()`
   - Keyboard and mouse input are ignored
   - All controller inputs trigger the same reaction

### Debounce Implementation

**Timing Constants:**
- `SLAP_DURATION_MS = 150`: Time before paw returns to idle (animation duration)
- `DEBOUNCE_MS = 50`: Minimum gap between slaps per paw

**Debounce Mechanism:**
- Track `last_slap_time` per paw (left, right, both)
- Use `time.time() * 1000` for millisecond precision
- Check elapsed time before triggering: `current_time - last_time >= DEBOUNCE_MS`
- Each paw has independent debounce (left/right can fire together)

**Active State Tracking:**
- `_left_paw_active`, `_right_paw_active`, `_both_paws_active` flags
- Prevents retrigger while animation is in progress
- Reset by calling `return_*_to_idle()` methods
- This provides double protection: debounce + active state

### Joystick Button Tracking

**Purpose:**
- Track pressed joystick buttons for controller visual integration (Task 5)
- Overlay can query `pressed_joystick_buttons: Set[str]` to highlight pressed buttons

**Implementation:**
- Add button to set when source is "joystick" and detail contains "_button"
- Axes are NOT tracked (only buttons for visual feedback)
- Set is cleared on `reset_state()`
- Tracking happens in JOYSTICK mode only (currently)

### Callback Architecture

**Design Pattern:**
- ReactionSystem owns callback references
- External code (OverlayWindow) provides callbacks for animations
- Callbacks: `left_paw_slap_callback`, `right_paw_slap_callback`, `both_paws_down_callback`
- Return callbacks: `left_paw_return_callback`, `right_paw_return_callback`, `both_paws_return_callback`

**Error Handling:**
- All callback invocations wrapped in try/except
- Errors logged but don't crash the system
- Robust against misbehaving callbacks

### Interface Contract with InputManager

**Connection:**
```python
# InputManager fires: callback(source, detail)
# ReactionSystem receives: on_input(source, detail)

input_manager = InputManager()
reaction_system = ReactionSystem(mode=config.mode)

# Connect InputManager to ReactionSystem
input_manager.on_input = reaction_system.on_input
```

**Callback Signature:**
- `source`: "keyboard", "mouse_button", "mouse_scroll", or "joystick"
- `detail`: Key name, button name, or joystick input identifier

### Testing Strategy

**Test Categories:**
1. **Initialization Tests:** Default mode, mode switching, callbacks
2. **Mode Routing Tests:** KBM vs JOYSTICK input handling
3. **Debounce Tests:** 50ms gap enforcement, independence between paws
4. **Active State Tests:** Prevent retrigger, return to idle
5. **Joystick Tracking Tests:** Button set management
6. **Error Handling Tests:** Callback exceptions don't crash

**Key Test Patterns:**
- Use `Mock` objects for callbacks to verify invocations
- Use `time.sleep(0.06)` to exceed debounce period
- Assert on `call_count` to verify debounce behavior
- Test both positive (triggers) and negative (ignored) cases

**Test Coverage:**
- 39 tests covering all major functionality
- All tests pass in < 1 second
- No external dependencies (no Qt, no pygame required)

## Avatar Renderer (Task 3)

### Qt Window Configuration

**Window Flags:**
- Use `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`
- `FramelessWindowHint`: Removes title bar and borders
- `WindowStaysOnTopHint`: Keeps window above all other windows
- `Tool`: Prevents window from appearing in taskbar (works with `FramelessWindowHint`)

**Transparency:**
- `setAttribute(Qt.WA_TranslucentBackground)` enables transparent background
- Set widget stylesheet to `"background: transparent;"` for full transparency
- Window must have fixed size (`setFixedSize()`) - resizing disabled by frameless flag

**Positioning:**
- Use `screen().availableGeometry()` to get screen dimensions (excludes taskbar/dock)
- Position formula: `x = screen_width - window_width - margin`, `y = screen_height - window_height - margin`
- Default margin from edge: 20 pixels

### Idle Breathing Animation

**Animation Parameters:**
- Timer interval: 16ms (~60 FPS) for smooth animation
- Sine wave frequency: 2.0 (controls breathing speed)
- Amplitude: 0.02 (±2% scale change for subtle effect)

**Implementation:**
- Use `QTimer.timeout.connect()` to trigger animation updates
- Scale formula: `scale = 1.0 + sin(time * speed) * amplitude`
- Apply scale via `QPixmap.scaled()` with `SmoothTransformation` for quality
- Only animate during idle pose; stop animation for other poses

**Performance:**
- Animation runs only when window is visible (`showEvent`/`hideEvent`)
- Timer stops when switching to non-idle poses
- Using pre-cached pixmaps avoids file I/O during animation

### Window Dragging

**Mouse Event Handling:**
- `mousePressEvent`: Store initial click position relative to window
- `mouseMoveEvent`: Update window position based on mouse movement
- `mouseReleaseEvent`: Clear drag state
- Must accept events to prevent them from propagating

**Implementation Pattern:**
```python
def mousePressEvent(self, event):
    if event.button() == Qt.LeftButton:
        self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
        event.accept()

def mouseMoveEvent(self, event):
    if event.buttons() & Qt.LeftButton and self._drag_position:
        self.move(event.globalPos() - self._drag_position)
        event.accept()
```

### Skin Management

**Folder Structure:**
```
assets/skins/<skin_name>/
├── skin.json          # Manifest with metadata and pose definitions
├── cat-idle.png       # Idle pose image
├── cat-left.png       # Left paw down pose
└── cat-right.png      # Right paw down pose
```

**Skin Manifest Format:**
```json
{
    "name": "Display Name",
    "author": "Creator Name",
    "version": "1.0",
    "poses": {
        "idle": {"file": "cat-idle.png", "width": 200, "height": 200},
        "left": {"file": "cat-left.png", "width": 200, "height": 200},
        "right": {"file": "cat-right.png", "width": 200, "height": 200}
    }
}
```

**Required Poses:**
- `idle`: Mandatory - default pose with breathing animation
- `left`: Optional but recommended - left paw action
- `right`: Optional but recommended - right paw action
- Skin fails to load if `idle` pose is missing

**Caching Strategy:**
- Load all pose pixmaps into memory when skin is loaded
- Store in `cached_pixmaps: Dict[str, QPixmap]` for O(1) access
- Clear cache when switching skins to free memory
- Use `resource_path()` for PyInstaller compatibility

### Qt Testing Requirements

**QApplication Requirement:**
- Qt widgets and QPixmap require a `QApplication` instance
- Tests must create `QApplication` before importing Qt widgets
- Use singleton pattern: `QApplication.instance()` to avoid multiple instances
- Pattern:
  ```python
  app = QApplication.instance()
  if app is None:
      app = QApplication(sys.argv)
  ```

**Testing Strategy:**
- Use temporary directories for test skins (pytest fixtures)
- Create placeholder images with PIL/Pillow for tests
- Mock callbacks to verify reaction triggers
- Test window state transitions (idle → action → idle)
- All tests completed in 6 seconds with 41 test cases

### Integration with ReactionSystem

**Callback Contract:**
- OverlayWindow provides callback methods (not just attributes)
- ReactionSystem calls: `trigger_left_paw_slap()`, `trigger_right_paw_slap()`, etc.
- Return methods: `return_left_paw()`, `return_right_paw()`, `return_both_paws()`
- Each trigger method stops animation and changes pose
- Return methods restart idle animation

**Error Handling:**
- All callbacks wrapped in try/except
- Errors logged but don't crash the application
- Robust against misconfigured or missing callbacks

## Skin System Enhancements (Task 6)

### Validation System

**Multi-Layer Validation:**
The `validate_skin_folder()` method checks four layers:
1. **Filesystem**: skin.json exists and readable
2. **JSON parsing**: Valid JSON syntax
3. **Schema**: Required fields (name, author, version, poses)
4. **Completeness**: All 3 poses (idle, left, right) defined with existing image files

**Validation Flow:**
```
load_skin(skin_name) 
  → validate_skin_folder() 
  → if invalid and skin_name != "default": 
      → fallback to load_skin("default")
  → if invalid and skin_name == "default": 
      → return False
```

**Error Handling:**
- Missing folder/file → validation returns False, load falls back to default
- Invalid JSON → logged as WARNING, validation returns False
- Missing required field → logged as WARNING, validation returns False
- Missing pose → logged as WARNING, validation returns False
- Missing image file → logged as WARNING, validation returns False

### Fallback Behavior

**Automatic Fallback:**
When a requested skin fails validation, the system automatically loads the default skin instead of failing completely:
- Prevents broken UI states
- Ensures avatar always has something to display
- Logs the failure for debugging

**Circular Fallback Prevention:**
The fallback only triggers when `skin_name != "default"`, preventing infinite recursion if the default skin itself is broken.

### API Methods

**New Methods (Task 6):**
1. `validate_skin_folder(folder_path)`: Full validation of skin structure
2. `get_current_skin_name()`: Returns currently loaded skin name (or None)
3. `reload()`: Force reload current skin (clears cache, reloads from disk)
4. Enhanced `list_available_skins()`: Only returns skins that pass validation

**Validation in list_available_skins:**
The `list_available_skins()` method now filters out invalid skins by calling `validate_skin_folder()` for each directory. This ensures:
- UI only shows valid, loadable skins
- Users cannot select broken skins
- Early detection of skin issues

### Testing Strategy

**Test Categories for Validation:**
1. **Validation Success**: Valid skin passes all checks
2. **Missing Manifest**: No skin.json file
3. **Invalid JSON**: Malformed JSON syntax
4. **Missing Required Field**: Missing name/author/version/poses
5. **Missing Pose**: Missing idle/left/right pose definition
6. **Missing Image File**: Image file referenced but doesn't exist
7. **Fallback Behavior**: Invalid skin falls back to default
8. **No Circular Fallback**: Broken default skin returns False

**Test Coverage:**
- 60 total tests in test_overlay.py
- 11 new tests for validation and new methods
- All tests pass in < 1 second
- Tests use temporary directories with PIL-generated placeholder images

### Neon Skin Example

**Second Test Skin:**
Created `assets/skins/neon/` with:
- Different color scheme (neon green, pink, blue)
- Same structure as default skin
- Demonstrates skin system supports multiple skins
- Used for testing skin switching

**Image Generation:**
Used PIL/Pillow to programmatically generate placeholder images:
- Simple cat face shape (circle + triangle ears)
- Different colors per pose
- 200x200 PNG format
- Demonstrates automated asset creation for testing

## Controller Visual (Task 5)

### Controller Mapping System

**JSON Mapping Format:**
```json
{
  "image": "xbox.png",
  "buttons": {
    "0": {
      "label": "A",
      "x": 0.65,
      "y": 0.72,
      "w": 0.08,
      "h": 0.08,
      "color": "#00FF00"
    }
  },
  "axes": {
    "0": {
      "label": "Left Stick X",
      "highlight": "both",
      "x": 0.22,
      "y": 0.49,
      "w": 0.16,
      "h": 0.16,
      "color": "#00BFFF"
    }
  },
  "hats": {
    "0": {
      "up": {"label": "D-Pad Up", "x": 0.33, "y": 0.65, "w": 0.08, "h": 0.08, "color": "#FFD700"},
      "down": {...},
      "left": {...},
      "right": {...}
    }
  }
}
```

**Coordinate System:**
- All positions use relative coordinates (0.0-1.0)
- `x`, `y`: Top-left corner position relative to image dimensions
- `w`, `h`: Width and height relative to image dimensions
- Example: `x=0.5` means 50% across the image width
- This allows mappings to work with any image size

**Validation Rules:**
- `image` field is mandatory
- All coordinates must be in range [0.0, 1.0]
- Button mapping must have: `label`, `x`, `y`, `w`, `h`, `color`
- Axis mapping must have: `label`, `highlight`, `x`, `y`, `w`, `h`, `color`
- `highlight` must be one of: "positive", "negative", "both"
- Hat mapping must have all four directions: `up`, `down`, `left`, `right`

### ControllerMap Model

**Architecture:**
- Separate dataclasses for different mapping types: `ButtonMapping`, `AxisMapping`, `HatMapping`
- Loads JSON mapping file using `resource_path()` for PyInstaller compatibility
- Validates structure and coordinates during loading
- Provides methods to query button positions and colors

**Key Methods:**
- `get_button_position(index)`: Returns (x, y, w, h) tuple for button
- `get_button_color(index)`: Returns hex color string for button
- `has_button(index)`: Checks if button exists in mapping
- `get_image_path()`: Returns absolute path to controller image

**Error Handling:**
- Raises `FileNotFoundError` if mapping file doesn't exist
- Raises `ValueError` if mapping has invalid structure or out-of-range coordinates
- Logs errors with specific details for debugging

### ControllerVisual Widget

**Widget Hierarchy:**
- Inherits from `QWidget`
- Contains `QLabel` for displaying controller image
- Override `paintEvent()` to draw button highlights
- Positioned behind avatar as background layer

**Highlight Rendering:**
- Use `QPainter` in `paintEvent()` to draw overlays
- `QColor.setAlpha(150)` for semi-transparent highlights
- Convert relative coordinates to absolute pixels based on widget size
- Highlight drawn only for buttons in `pressed_buttons` set

**Button ID Parsing:**
- Button IDs follow format: `joy{index}_button{num}`
- Parse using regex: `r"_button(\d+)"` to extract button index
- Example: `"joy0_button0"` → button index 0

**Integration with ReactionSystem:**
- ReactionSystem maintains `pressed_joystick_buttons: Set[str]`
- Call `widget.update_pressed_buttons(pressed_set)` to update highlights
- Widget triggers repaint when button set changes
- Only visible in JOYSTICK mode

### Controller Image Generation

**Placeholder Images:**
- Use PIL/Pillow to create simple controller silhouettes
- Xbox controller: Standard gamepad shape with A/B/X/Y buttons
- DS5 controller: DualShock-style with Cross/Circle/Square/Triangle
- 400x300 pixel size for placeholder
- Transparent background for overlay compatibility

**Design Considerations:**
- Avoid copyrighted images - create original silhouettes
- Use semi-transparent shapes to distinguish controller areas
- Outline buttons/sticks with different colors for clarity
- Keep file size small (~3KB PNG)

### Testing Strategy

**Test Categories:**
1. **Dataclass Tests:** ButtonMapping, AxisMapping, HatMapping creation
2. **ControllerMap Tests:** Loading, validation, position/color queries
3. **ControllerVisual Tests:** Widget creation, button updates, visibility
4. **Integration Tests:** Real mapping files, coordinate validation

**Key Test Patterns:**
- Use `tempfile.NamedTemporaryFile` for temporary mapping files
- Test both valid and invalid JSON structures
- Verify coordinate range validation (0.0-1.0)
- Test button ID parsing with regex
- Mock `QApplication` for Qt widget tests

**Test Coverage:**
- 23 tests covering all functionality
- All tests pass in < 1 second
- Qt tests use session-scoped QApplication fixture
- No external dependencies (no pygame required)

### Mode Toggle Implementation

**Keyboard Shortcut:**
- Default: `Ctrl+Shift+M` (from `toggle_shortcut` config)
- Toggles between "kbm" and "controller" modes
- Updates `ConfigManager.mode` and saves to config file
- Shows/hides ControllerVisual based on mode

**Visibility Logic:**
- ControllerVisual only visible in JOYSTICK mode
- Hidden by default in KBM mode
- Toggle updates both config and widget visibility
- Mode persists across application restarts

### Asset Management

**Directory Structure:**
```
assets/controllers/
├── xbox.png          # Xbox controller image
├── xbox_map.json     # Xbox button mapping
├── ds5.png           # DualShock 5 image
└── ds5_map.json      # DS5 button mapping
```

**Resource Path Handling:**
- Use `resource_path()` for all asset paths
- Works in both development and PyInstaller bundled environments
- Development: relative to project root
- Bundled: relative to `_MEIPASS` temp directory

## Integration (Task 7)

### Component Initialization Order

**Strict Order (MUST follow):**
1. `QApplication` - MUST be first (Qt requirement for all widgets/pixmaps)
2. `ConfigManager` - Load persisted settings
3. `SkinManager` + load skin - Load avatar images (requires QApplication for QPixmap)
4. `OverlayWindow` - Main window (requires skin_manager)
5. `ControllerVisual` - Controller overlay (child of OverlayWindow)
6. `InputManager` - Input listeners (no dependencies)
7. `ReactionSystem` - Reaction coordinator (connects InputManager → OverlayWindow)

**Why This Order:**
- Qt requires QApplication before any QPixmap or widget creation
- SkinManager loads QPixmaps, so needs QApplication
- OverlayWindow needs skin_manager for initial display
- ControllerVisual must be created after OverlayWindow to be parented correctly
- InputManager is independent and can be created anytime
- ReactionSystem must be last to connect all callbacks

### Callback Wiring Pattern

**One-Way Data Flow:**
```
InputManager.on_input → ReactionSystem.on_input → OverlayWindow.trigger_* → ReactionSystem.return_* → OverlayWindow.return_to_idle
```

**Connection Code:**
```python
# Input → Reaction
input_manager.on_input = reaction_system.on_input

# Reaction → Animation
reaction_system.left_paw_slap_callback = window.trigger_left_paw_slap
reaction_system.right_paw_slap_callback = window.trigger_right_paw_slap
reaction_system.both_paws_down_callback = window.trigger_both_paws_down

# Return callbacks
window.trigger_left_paw_slap_callback = reaction_system.return_left_paw_to_idle
window.trigger_right_paw_slap_callback = reaction_system.return_right_paw_to_idle
window.trigger_both_paws_down_callback = reaction_system.return_both_paws_to_idle
```

### Joystick Disconnect Handling

**Architecture:**
1. `JoystickListener._handle_joystick_removed()` calls `on_disconnect` callback
2. `main.py` wires: `input_manager.joystick_listener.on_disconnect = reaction_system.on_joystick_disconnect`
3. `ReactionSystem.on_joystick_disconnect()` checks mode and auto-switches to KBM

**Implementation:**
```python
def on_joystick_disconnect(self) -> None:
    if self.mode == InputMode.JOYSTICK:
        logger.info("Controller disconnected, switching to KBM mode")
        self.set_mode("kbm")
        self.pressed_joystick_buttons.clear()
```

### Mode Toggle Hotkey

**Implementation:**
- Config stores: `toggle_shortcut = "ctrl+shift+m"`
- Keyboard listener fires callbacks for each key press
- Track pressed keys in `_active_keys: Set[str]`
- Check if all required keys are pressed when any key fires

**Code Pattern:**
```python
def check_mode_toggle_hotkey(config: ConfigManager, reaction_system: ReactionSystem):
    toggle_shortcut = config.toggle_shortcut.lower()
    parts = toggle_shortcut.split("+")
    required_keys = set(parts)
    
    if required_keys.issubset(_active_keys):
        current_mode = reaction_system.get_mode()
        new_mode = "kbm" if current_mode == "controller" else "controller"
        reaction_system.set_mode(new_mode)
        config.set("mode", new_mode)
```

### Window Position Persistence

**Flow:**
1. On launch: `_position_bottom_right()` checks config for saved position
2. If valid (x, y >= 0): restore position with screen bounds clamping
3. On close: `closeEvent()` saves current position to config

**Implementation:**
```python
def closeEvent(self, event):
    self.stop_animation()
    if self.config:
        self.config.set("window_x", self.x())
        self.config.set("window_y", self.y())
    super().closeEvent(event)

def _position_bottom_right(self):
    if self.config and self.config.window_x >= 0 and self.config.window_y >= 0:
        x = self.config.window_x
        y = self.config.window_y
        # Clamp to screen bounds
        x = max(screen_x, min(x, screen_x + screen_w - window_w))
        y = max(screen_y, min(y, screen_y + screen_h - window_h))
    else:
        # Default: bottom-right corner
        x = screen_x + screen_w - window_w - margin
        y = screen_y + screen_h - window_h - margin
    self.move(x, y)
```

### Cleanup on Exit

**atexit Handler:**
```python
def cleanup():
    logger.info("Shutting down BongoSteam...")
    input_manager.stop()
    logger.info("BongoSteam shutdown complete")

atexit.register(cleanup)
```

**Important:**
- `input_manager.stop()` stops all listeners (keyboard, mouse, joystick)
- Daemon threads auto-terminate when main thread exits
- No explicit `pygame.quit()` needed (handled by JoystickListener)

### Integration Tests

**Test Categories:**
1. **Component Initialization:** Verify each component initializes correctly
2. **Component Wiring:** Test InputManager → ReactionSystem → OverlayWindow chain
3. **Config Persistence:** Window position, mode changes, launch count
4. **ControllerVisual:** Visibility by mode, button highlighting
5. **Cleanup:** Thread termination, no zombie processes

**Key Test Patterns:**
- Use `tempfile.TemporaryDirectory()` for config files
- Use `PIL.Image` to create test skins
- Session-scoped `QApplication` fixture
- Mock callbacks to verify wiring

**Test Coverage:**
- 16 tests in test_integration.py
- All tests pass in < 1 second
- Covers initialization, wiring, persistence, cleanup
