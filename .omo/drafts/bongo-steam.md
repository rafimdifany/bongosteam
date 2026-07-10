---
slug: bongo-steam
status: approved
intent: clear
pending-action: done
approach: Windows desktop app, Python/PyQt5/pynput/pygame, 6 components, 2 modes (Keyboard+Mouse / Joystick), manual toggle via shortcut, controller visual with button highlights (Xbox + DS5), manual QA only
---

# Draft: bongo-steam

## Components
| id | outcome | status | evidence |
| -- | ------- | ------ | -------- |
| 1. Input Tracking | Kbd+mouse (pynput) + joystick (pygame) with hotplugging | active | reference bongo_cat/input/, librarian research |
| 2. Avatar Rendering | Frameless always-on-top Qt window, bongocat 3-pose | active | reference bongo_cat/ui/main_window.py |
| 3. Controller Visual | Overlay controller image (Xbox/DS5) + button highlight regions | active | user requirement |
| 4. Reaction System | Mode-based dispatching with debounce | active | user requirement |
| 5. Configuration | INI config, mode toggle shortcut | active | reference config.py |
| 6. Build | PyInstaller standalone .exe | active | reference bongo_cat.spec |

## Decisions (with rationale)
1. Clone bongocat avatar — user choice
2. Minimal scope — no achievements/combo/sound per user
3. Controller visual mandatory Phase 1 — user requirement
4. Manual mode toggle via Ctrl+Shift+M default — user choice
5. Controller placeholder assets — user replaces later
6. Mouse: all clicks + scroll wheel (50ms debounce per scroll tick) — user choice
7. Manual QA + unit tests for config/mapping logic — user choice
8. PyQt5 for GUI + pygame for joystick ONLY (no display init, background thread) — proven by reference
9. Window: NOT click-through, always-on-top, draggable via titlebar/dedicated area — reference pattern
10. Admin: required for pynput global hooks, documented, graceful degraded mode if not admin
11. Axes deadzone: 0.3 threshold, one-shot per rising edge, re-arm on return to center
12. Joystick disconnect: auto-switch to KBM mode, show transient notification

## Metis findings (folded)
- PyQt5+pygame: safe because pygame used ONLY for joystick subsystem, no display init (proven by bongocat)
- Drag vs click-through: resolved by NOT using click-through; pynput handles global input; window is draggable
- Admin privilege: documented with fallback; include UAC manifest in PyInstaller build
- Performance: QTimer 16ms, dirty-rect rendering, <5% CPU idle, <100MB RAM target
- 8 ambiguities all resolved above (scroll debounce, mode switching, disconnect behavior, etc.)

## Scope IN / OUT
See plan file for full details.
