"""Mouse input listener using pynput."""

import logging
import time
from typing import Callable, Set, Optional
from pynput import mouse

logger = logging.getLogger(__name__)


class MouseListener:
    """Listens for global mouse events using pynput.

    Monitors mouse clicks and scroll events globally (non-blocking),
    triggering callbacks on button press events while avoiding duplicates.

    Note:
        On Windows, pynput requires administrator privileges for global hooks.
        The listener runs in a daemon thread and does not block the main thread.

    Attributes:
        callback: Function called on mouse events with (source, detail) arguments
        active_buttons: Set of currently pressed buttons (for debounce)
        last_scroll_time: Timestamp of last scroll event (for debounce)
        scroll_debounce_ms: Minimum milliseconds between scroll callbacks
        listener: pynput mouse listener instance
    """

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        """Initialize mouse listener.

        Args:
            callback: Function to call when mouse event occurs.
                Receives two arguments:
                - source: "mouse_button" or "mouse_scroll"
                - detail: button name ("left", "right", "middle") or direction ("up", "down")
        """
        self.callback = callback
        self.active_buttons: Set[str] = set()
        self.last_scroll_time: float = 0.0
        self.scroll_debounce_ms: float = 50.0
        self.listener: Optional[mouse.Listener] = None

    def _get_button_name(self, button: mouse.Button) -> str:
        """Convert pynput mouse button to string name.

        Args:
            button: pynput Button enum

        Returns:
            String representation: "left", "right", or "middle"
        """
        if button == mouse.Button.left:
            return "left"
        elif button == mouse.Button.right:
            return "right"
        elif button == mouse.Button.middle:
            return "middle"
        else:
            return str(button)

    def on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Handle mouse click events.

        Args:
            x: X coordinate of click
            y: Y coordinate of click
            button: Mouse button that was clicked
            pressed: True if pressed, False if released
        """
        button_name = self._get_button_name(button)

        if pressed:
            # Only fire callback if button not already active (debounce)
            if button_name not in self.active_buttons:
                self.active_buttons.add(button_name)
                try:
                    self.callback("mouse_button", button_name)
                except Exception as e:
                    logger.error(f"Error in mouse button callback: {e}")
        else:
            # Remove from active set on release
            self.active_buttons.discard(button_name)

    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse scroll events with debounce.

        Args:
            x: X coordinate of scroll
            y: Y coordinate of scroll
            dx: Horizontal scroll amount (unused)
            dy: Vertical scroll amount (positive = up, negative = down)
        """
        current_time = time.time()

        # Check debounce
        time_since_last = (current_time - self.last_scroll_time) * 1000
        if time_since_last < self.scroll_debounce_ms:
            return

        # Update last scroll time
        self.last_scroll_time = current_time

        # Determine scroll direction
        if dy > 0:
            direction = "up"
        elif dy < 0:
            direction = "down"
        else:
            return  # No vertical scroll

        try:
            self.callback("mouse_scroll", direction)
        except Exception as e:
            logger.error(f"Error in mouse scroll callback: {e}")

    def start(self) -> None:
        """Start listening for mouse events.

        Creates a pynput mouse listener in a daemon thread.
        Does not block the main thread.
        """
        if self.listener is None or not self.listener.is_alive():
            self.listener = mouse.Listener(
                on_click=self.on_click,
                on_scroll=self.on_scroll,
                suppress=False,  # Don't suppress input to other apps
            )
            self.listener.start()
            logger.info("Mouse listener started")

    def stop(self) -> None:
        """Stop listening for mouse events."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            self.listener = None
            logger.info("Mouse listener stopped")

    def is_running(self) -> bool:
        """Check if listener is currently active.

        Returns:
            True if listener is running, False otherwise
        """
        return self.listener is not None and self.listener.is_alive()
