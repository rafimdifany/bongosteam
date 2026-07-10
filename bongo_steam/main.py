"""Main entry point for BongoSteam application."""

import atexit
import logging
import sys
from typing import Set

from PyQt5.QtWidgets import QApplication

from .models.config import ConfigManager
from .models.skin_manager import SkinManager
from .input.input_manager import InputManager
from .reaction.reaction_system import ReactionSystem
from .ui.overlay_window import OverlayWindow
from .ui.controller_visual import ControllerVisual

logger = logging.getLogger("BongoSteam")

_active_keys: Set[str] = set()


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def check_mode_toggle_hotkey(config: ConfigManager, reaction_system: ReactionSystem) -> None:
    """Check if mode toggle hotkey is pressed and toggle mode if so.
    
    Args:
        config: ConfigManager instance with toggle_shortcut setting
        reaction_system: ReactionSystem instance to toggle mode on
    """
    toggle_shortcut = config.toggle_shortcut.lower()
    parts = toggle_shortcut.split("+")
    
    required_keys = set(parts)
    if required_keys.issubset(_active_keys):
        current_mode = reaction_system.get_mode()
        new_mode = "kbm" if current_mode == "controller" else "controller"
        reaction_system.set_mode(new_mode)
        config.set("mode", new_mode)
        logger.info(f"Mode toggled to: {new_mode}")


def main() -> int:
    """Main entry point for BongoSteam application.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    setup_logging()
    
    app = QApplication(sys.argv)
    
    config = ConfigManager()
    config.launch_count += 1
    config.save()
    
    skin_manager = SkinManager()
    if not skin_manager.load_skin(config.skin):
        logger.warning(f"Failed to load skin '{config.skin}', using default")
    
    window = OverlayWindow(skin_manager=skin_manager, config=config)
    
    controller_visual = ControllerVisual(
        controller_type=config.controller_type,
        parent=window
    )
    controller_visual.setGeometry(0, 0, window.width(), window.height())
    controller_visual.lower()
    controller_visual.setVisible(config.mode == "controller")
    
    def on_mode_change(new_mode: str) -> None:
        if new_mode == "controller":
            controller_visual.setVisible(True)
            controller_visual.clear_highlights()
        else:
            controller_visual.setVisible(False)
    
    reaction_system = ReactionSystem(mode=config.mode)
    reaction_system.on_mode_change = on_mode_change
    
    def handle_input_with_tracking(source: str, detail: str) -> None:
        if source == "keyboard":
            _active_keys.add(detail)
            check_mode_toggle_hotkey(config, reaction_system)
        elif source in ("mouse_button", "mouse_scroll"):
            _active_keys.discard(detail)
        
        reaction_system.on_input(source, detail)
    
    input_manager = InputManager()
    # Connect thread-safe signal to handler (replaces direct callback assignment)
    input_manager.on_input_signal.connect(handle_input_with_tracking)
    
    input_manager.joystick_listener.on_disconnect = reaction_system.on_joystick_disconnect
    
    window.trigger_left_paw_slap_callback = reaction_system.return_left_paw_to_idle
    window.trigger_right_paw_slap_callback = reaction_system.return_right_paw_to_idle
    window.trigger_both_paws_down_callback = reaction_system.return_both_paws_to_idle
    
    # Connect reaction system callbacks to overlay window methods
    reaction_system.left_paw_slap_callback = window.trigger_left_paw_slap
    reaction_system.right_paw_slap_callback = window.trigger_right_paw_slap
    reaction_system.both_paws_down_callback = window.trigger_both_paws_down
    reaction_system.left_paw_return_callback = window.return_left_paw
    reaction_system.right_paw_return_callback = window.return_right_paw
    reaction_system.both_paws_return_callback = window.return_both_paws
    
    def on_key_release(source: str, detail: str) -> None:
        if source == "keyboard":
            _active_keys.discard(detail)
    
    original_keyboard_on_press = input_manager.keyboard_listener.on_press
    def keyboard_on_press_with_release(key) -> None:
        original_keyboard_on_press(key)
    
    original_keyboard_on_release = input_manager.keyboard_listener.on_release
    def keyboard_on_release_with_tracking(key) -> None:
        original_keyboard_on_release(key)
        key_name = input_manager.keyboard_listener._get_key_name(key)
        _active_keys.discard(key_name)
    
    input_manager.keyboard_listener.on_press = keyboard_on_press_with_release
    input_manager.keyboard_listener.on_release = keyboard_on_release_with_tracking
    
    def cleanup() -> None:
        logger.info("Shutting down BongoSteam...")
        input_manager.stop()
        logger.info("BongoSteam shutdown complete")
    
    atexit.register(cleanup)
    
    input_manager.start()
    window.show()
    
    logger.info(
        f"BongoSteam started (launch #{config.launch_count}, "
        f"mode={config.mode}, skin={config.skin})"
    )
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
