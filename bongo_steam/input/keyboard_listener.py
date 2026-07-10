"""Keyboard input listener using pynput."""

import logging
from typing import Callable, Set, Optional
from pynput import keyboard

logger = logging.getLogger(__name__)


class KeyboardListener:
    """Listens for global keyboard events using pynput.

    Monitors keyboard input globally (non-blocking), triggering callbacks
    on key press events while avoiding duplicates via active_keys tracking.

    Note:
        On Windows, pynput requires administrator privileges for global hooks.
        The listener runs in a daemon thread and does not block the main thread.

    Attributes:
        callback: Function called on key press with (source, key_name) arguments
        active_keys: Set of currently pressed keys (for debounce)
        listener: pynput keyboard listener instance
    """

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        """Initialize keyboard listener.

        Args:
            callback: Function to call when a key is pressed.
                Receives two arguments: source ("keyboard") and key_name (str).
        """
        self.callback = callback
        self.active_keys: Set[str] = set()
        self.listener: Optional[keyboard.Listener] = None

    def _get_key_name(self, key) -> str:
        """Convert pynput key to string name.

        Args:
            key: pynput Key enum or KeyCode instance

        Returns:
            String representation of the key (e.g., "a", "space", "shift")
        """
        if isinstance(key, keyboard.Key):
            # Handle special keys (Key.space, Key.shift, etc.)
            return key.name
        elif isinstance(key, keyboard.KeyCode):
            # Handle regular characters
            if key.char:
                return key.char.lower()
            elif key.vk:
                # Virtual key code as fallback
                return f"vk_{key.vk}"
        # Fallback to string representation
        return str(key)

    def on_press(self, key) -> None:
        """Handle key press events.

        Args:
            key: The key that was pressed (pynput Key or KeyCode)
        """
        key_name = self._get_key_name(key)

        # Only fire callback if key not already active (debounce)
        if key_name not in self.active_keys:
            self.active_keys.add(key_name)
            try:
                self.callback("keyboard", key_name)
            except Exception as e:
                logger.error(f"Error in keyboard callback: {e}")

    def on_release(self, key) -> None:
        """Handle key release events.

        Args:
            key: The key that was released
        """
        key_name = self._get_key_name(key)
        self.active_keys.discard(key_name)

    def start(self) -> None:
        """Start listening for keyboard events.

        Creates a pynput keyboard listener in a daemon thread.
        Does not block the main thread.
        """
        if self.listener is None or not self.listener.is_alive():
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release,
                suppress=False,  # Don't suppress input to other apps
            )
            self.listener.start()
            logger.info("Keyboard listener started")

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            self.listener = None
            logger.info("Keyboard listener stopped")

    def is_running(self) -> bool:
        """Check if listener is currently active.

        Returns:
            True if listener is running, False otherwise
        """
        return self.listener is not None and self.listener.is_alive()
