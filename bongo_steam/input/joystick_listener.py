"""Joystick/gamepad input listener using pygame."""

import logging
import threading
import time
from typing import Callable, Dict, Set, Optional

logger = logging.getLogger(__name__)

# Try to import pygame
try:
    import pygame
    import pygame.joystick
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame not available - joystick support disabled")


class JoystickListener:
    """Listens for joystick/gamepad input using pygame.

    Monitors joystick buttons and axes with hotplugging support,
    running polling in a background daemon thread at ~125Hz.

    Note:
        Only initializes pygame.joystick, NOT pygame.display.
        Supports hotplugging via JOYDEVICEADDED/REMOVED events (pygame 2.0+).

    Attributes:
        callback: Function called on joystick events with (source, detail) arguments
        on_disconnect: Optional callback for joystick disconnect notifications (no args)
        running: Whether the listener thread is active
        thread: Background polling thread
        joysticks: Dict mapping joystick instance_id to pygame.Joystick objects
        pressed_buttons: Dict mapping joystick instance_id to set of pressed button names
        active_axes: Dict mapping joystick instance_id to set of active axis names
        last_axes_values: Dict mapping joystick instance_id to axis value dicts
        poll_interval_ms: Polling interval in milliseconds (8ms = ~125Hz)
        axis_deadzone: Deadzone threshold for axis movement (0.3 = 30%)
    """

    # Pygame event types for hotplugging
    JOYDEVICEADDED = 1536
    JOYDEVICEREMOVED = 1537

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        """Initialize joystick listener.

        Args:
            callback: Function to call when joystick event occurs.
                Receives two arguments:
                - source: always "joystick"
                - detail: button/axis name (e.g., "joy0_button0", "joy0_axis0")
        """
        self.callback = callback
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Joystick tracking
        self.joysticks: Dict[int, pygame.joystick.Joystick] = {}
        self.pressed_buttons: Dict[int, Set[str]] = {}
        self.active_axes: Dict[int, Set[str]] = {}
        self.last_axes_values: Dict[int, Dict[int, float]] = {}

        # Polling configuration
        self.poll_interval_ms: float = 8.0  # 8ms = ~125Hz
        self.axis_deadzone: float = 0.3  # 30% deadzone

    def _initialize_pygame(self) -> None:
        """Initialize pygame joystick subsystem (no display)."""
        if not PYGAME_AVAILABLE:
            return

        # Only initialize joystick subsystem, NOT display
        pygame.joystick.init()
        logger.info("Pygame joystick subsystem initialized")

    def _poll_loop(self) -> None:
        """Main polling loop (runs in background thread)."""
        if not PYGAME_AVAILABLE:
            logger.warning("pygame not available - joystick listener exiting")
            return

        try:
            self._initialize_pygame()

            while self.running:
                # Process pygame events (for hotplugging)
                self._process_events()

                # Poll all connected joysticks
                self._poll_joysticks()

                # Sleep for poll interval
                time.sleep(self.poll_interval_ms / 1000.0)

        except Exception as e:
            logger.error(f"Joystick listener error: {e}")
        finally:
            # Cleanup pygame joystick subsystem
            if PYGAME_AVAILABLE:
                pygame.joystick.quit()

    def _process_events(self) -> None:
        """Process pygame events for hotplugging."""
        if not PYGAME_AVAILABLE:
            return

        for event in pygame.event.get():
            if event.type == self.JOYDEVICEADDED:
                self._handle_joystick_added(event.device_index)
            elif event.type == self.JOYDEVICEREMOVED:
                self._handle_joystick_removed(event.instance_id)

    def _handle_joystick_added(self, device_index: int) -> None:
        """Handle joystick connection event.

        Args:
            device_index: pygame device index for new joystick
        """
        if not PYGAME_AVAILABLE:
            return

        try:
            joystick = pygame.joystick.Joystick(device_index)
            joystick.init()
            instance_id = joystick.get_instance_id()

            # Track joystick
            self.joysticks[instance_id] = joystick
            self.pressed_buttons[instance_id] = set()
            self.active_axes[instance_id] = set()
            self.last_axes_values[instance_id] = {}

            logger.info(f"Joystick connected: {joystick.get_name()} (instance_id={instance_id})")
        except Exception as e:
            logger.error(f"Error adding joystick {device_index}: {e}")

    def _handle_joystick_removed(self, instance_id: int) -> None:
        """Handle joystick disconnection event.

        Args:
            instance_id: pygame instance_id of removed joystick
        """
        # Remove from tracking dicts
        self.joysticks.pop(instance_id, None)
        self.pressed_buttons.pop(instance_id, None)
        self.active_axes.pop(instance_id, None)
        self.last_axes_values.pop(instance_id, None)

        logger.info(f"Joystick disconnected (instance_id={instance_id})")

        # Call disconnect callback if set
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Error in on_disconnect callback: {e}")

    def _poll_joysticks(self) -> None:
        """Poll all connected joysticks for button and axis state."""
        if not PYGAME_AVAILABLE:
            return

        # Detect newly connected joysticks (fallback if events missed)
        joystick_count = pygame.joystick.get_count()
        connected_ids = set(self.joysticks.keys())

        # Check for new joysticks
        for i in range(joystick_count):
            try:
                temp_joy = pygame.joystick.Joystick(i)
                temp_joy.init()
                instance_id = temp_joy.get_instance_id()
                if instance_id not in connected_ids:
                    # Found new joystick not tracked
                    self._handle_joystick_added(i)
            except Exception:
                pass

        # Poll tracked joysticks
        for instance_id, joystick in list(self.joysticks.items()):
            try:
                self._poll_joystick_buttons(instance_id, joystick)
                self._poll_joystick_axes(instance_id, joystick)
            except Exception as e:
                logger.debug(f"Error polling joystick {instance_id}: {e}")

    def _poll_joystick_buttons(self, instance_id: int, joystick: pygame.joystick.Joystick) -> None:
        """Poll buttons for a joystick.

        Args:
            instance_id: Joystick instance ID
            joystick: Pygame Joystick object
        """
        pressed_set = self.pressed_buttons.get(instance_id, set())
        joy_index = list(self.joysticks.keys()).index(instance_id)

        for button_idx in range(joystick.get_numbuttons()):
            button_name = f"joy{joy_index}_button{button_idx}"
            is_pressed = joystick.get_button(button_idx)

            if is_pressed and button_name not in pressed_set:
                # Button just pressed (rising edge)
                pressed_set.add(button_name)
                try:
                    self.callback("joystick", button_name)
                except Exception as e:
                    logger.error(f"Error in joystick button callback: {e}")
            elif not is_pressed and button_name in pressed_set:
                # Button released
                pressed_set.discard(button_name)

    def _poll_joystick_axes(self, instance_id: int, joystick: pygame.joystick.Joystick) -> None:
        """Poll axes for a joystick with deadzone handling.

        Args:
            instance_id: Joystick instance ID
            joystick: Pygame Joystick object
        """
        active_set = self.active_axes.get(instance_id, set())
        last_values = self.last_axes_values.get(instance_id, {})
        joy_index = list(self.joysticks.keys()).index(instance_id)

        for axis_idx in range(joystick.get_numaxes()):
            axis_value = joystick.get_axis(axis_idx)
            last_value = last_values.get(axis_idx, 0.0)

            # Determine axis direction
            axis_name = None
            is_active = False

            if abs(axis_value) > self.axis_deadzone:
                # Axis outside deadzone
                direction = 1 if axis_value > 0 else -1
                axis_name = f"joy{joy_index}_axis{axis_idx}"
                is_active = True

            # Fire on rising edge (entering active zone from deadzone)
            if is_active and abs(last_value) <= self.axis_deadzone:
                if axis_name and axis_name not in active_set:
                    active_set.add(axis_name)
                    try:
                        self.callback("joystick", axis_name)
                    except Exception as e:
                        logger.error(f"Error in joystick axis callback: {e}")
            elif not is_active and abs(last_value) > self.axis_deadzone:
                # Re-arm when back in deadzone
                axis_name_prev = f"joy{joy_index}_axis{axis_idx}"
                active_set.discard(axis_name_prev)

            # Update last value
            last_values[axis_idx] = axis_value

    def start(self) -> None:
        """Start the joystick listener in a background thread."""
        if not PYGAME_AVAILABLE:
            logger.warning("Cannot start joystick listener - pygame not available")
            return

        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()
            logger.info("Joystick listener started")

    def stop(self) -> None:
        """Stop the joystick listener."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1.0)
                self.thread = None
            logger.info("Joystick listener stopped")

    def is_running(self) -> bool:
        """Check if listener is currently active.

        Returns:
            True if listener is running, False otherwise
        """
        return self.running
