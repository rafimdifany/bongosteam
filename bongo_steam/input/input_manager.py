"""Input manager coordinator for all input listeners."""

import logging
from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .keyboard_listener import KeyboardListener
from .mouse_listener import MouseListener
from .joystick_listener import JoystickListener

logger = logging.getLogger(__name__)


class InputManager(QObject):
    """Coordinates keyboard, mouse, and joystick input listeners.

    Manages lifecycle of all input listeners and provides unified
    callback interface for input events.

    Attributes:
        callback: Function called on any input event with (source, detail) arguments
        keyboard_listener: Keyboard input listener
        mouse_listener: Mouse input listener
        joystick_listener: Joystick input listener
        on_input: Optional callback for external connection (deprecated, use on_input_signal)
        on_input_signal: Thread-safe signal for input events (emits source, detail)
    """
    
    # Thread-safe signal for input events (from background threads to main thread)
    on_input_signal = pyqtSignal(str, str)

    def __init__(self, callback: Optional[Callable[[str, str], None]] = None) -> None:
        """Initialize input manager with optional callback.

        Args:
            callback: Optional function to call on any input event.
                Receives two arguments:
                - source: "keyboard", "mouse_button", "mouse_scroll", or "joystick"
                - detail: key name, button name, scroll direction, or joystick input name
        """
        super().__init__()
        
        # Store callback (legacy support)
        self.callback = callback
        self.on_input: Optional[Callable[[str, str], None]] = None

        # Create listeners with internal callback
        self.keyboard_listener = KeyboardListener(self._handle_input)
        self.mouse_listener = MouseListener(self._handle_input)
        self.joystick_listener = JoystickListener(self._handle_input)

        logger.info("Input manager initialized")

    def _handle_input(self, source: str, detail: str) -> None:
        """Internal handler that dispatches to callbacks.

        Args:
            source: Input source identifier
            detail: Input detail (key name, button, etc.)
        """
        # Emit thread-safe signal (background threads → main thread)
        try:
            self.on_input_signal.emit(source, detail)
        except Exception as e:
            logger.error(f"Error emitting input signal: {e}")
        
        # Call the callback if provided (for backward compatibility)
        if self.callback:
            try:
                self.callback(source, detail)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
        
        # Call on_input if connected (for backward compatibility)
        if self.on_input:
            try:
                self.on_input(source, detail)
            except Exception as e:
                logger.error(f"Error in on_input callback: {e}")

    def start(self) -> None:
        """Start all input listeners."""
        logger.info("Starting all input listeners...")

        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.joystick_listener.start()

        logger.info("All input listeners started")

    def stop(self) -> None:
        """Stop all input listeners."""
        logger.info("Stopping all input listeners...")

        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.joystick_listener.stop()

        logger.info("All input listeners stopped")

    def is_running(self) -> bool:
        """Check if any listener is currently running.

        Returns:
            True if at least one listener is active, False otherwise
        """
        return (
            self.keyboard_listener.is_running()
            or self.mouse_listener.is_running()
            or self.joystick_listener.is_running()
        )

    def get_status(self) -> dict:
        """Get status of all listeners.

        Returns:
            Dictionary with status of each listener

        Example:
            >>> manager.get_status()
            {'keyboard': True, 'mouse': True, 'joystick': False}
        """
        return {
            'keyboard': self.keyboard_listener.is_running(),
            'mouse': self.mouse_listener.is_running(),
            'joystick': self.joystick_listener.is_running(),
        }
