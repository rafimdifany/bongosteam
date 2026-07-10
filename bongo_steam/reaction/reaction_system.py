"""Reaction system coordinator with mode-based input routing."""

import logging
import time
from enum import Enum
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)


class InputMode(Enum):
    """Input mode for reaction system."""
    
    KBM = "kbm"  # Keyboard and Mouse
    JOYSTICK = "controller"  # Joystick/Controller


class ReactionSystem:
    """Coordinates input events to visual reactions with mode-based routing.
    
    Manages a state machine with two modes: KBM and JOYSTICK.
    Routes input to appropriate paw reactions based on current mode.
    Implements debounce and timing for smooth animations.
    
    Attributes:
        mode: Current input mode (KBM or JOYSTICK)
        left_paw_slap_callback: Callback for left paw slap animation
        right_paw_slap_callback: Callback for right paw slap animation
        both_paws_down_callback: Callback for both paws down animation
        left_paw_return_callback: Callback to return left paw to idle
        right_paw_return_callback: Callback to return right paw to idle
        both_paws_return_callback: Callback to return both paws to idle
        on_mode_change: Optional callback for mode changes (receives new_mode string)
        pressed_joystick_buttons: Set of currently pressed joystick buttons
    """
    
    SLAP_DURATION_MS = 150  # Duration before returning to idle
    DEBOUNCE_MS = 50  # Minimum gap between slaps per paw
    
    def __init__(
        self,
        mode: str = "kbm",
        left_paw_slap_callback: Optional[Callable[[], None]] = None,
        right_paw_slap_callback: Optional[Callable[[], None]] = None,
        both_paws_down_callback: Optional[Callable[[], None]] = None,
        left_paw_return_callback: Optional[Callable[[], None]] = None,
        right_paw_return_callback: Optional[Callable[[], None]] = None,
        both_paws_return_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize reaction system with mode and animation callbacks.
        
        Args:
            mode: Initial input mode ("kbm" or "controller")
            left_paw_slap_callback: Called when left paw should slap
            right_paw_slap_callback: Called when right paw should slap
            both_paws_down_callback: Called when both paws should go down
            left_paw_return_callback: Called to return left paw to idle
            right_paw_return_callback: Called to return right paw to idle
            both_paws_return_callback: Called to return both paws to idle
        """
        # Set mode
        self.mode = InputMode(mode.lower() if mode.lower() in ("kbm", "controller") else "kbm")
        
        # Store callbacks
        self.left_paw_slap_callback = left_paw_slap_callback
        self.right_paw_slap_callback = right_paw_slap_callback
        self.both_paws_down_callback = both_paws_down_callback
        self.left_paw_return_callback = left_paw_return_callback
        self.right_paw_return_callback = right_paw_return_callback
        self.both_paws_return_callback = both_paws_return_callback
        self.on_mode_change: Optional[Callable[[str], None]] = None
        
        # Timing for debounce and slap duration
        self._last_left_slap_time: float = 0.0
        self._last_right_slap_time: float = 0.0
        self._last_both_slap_time: float = 0.0
        
        # Track pressed joystick buttons for visual integration
        self.pressed_joystick_buttons: Set[str] = set()
        
        # Track which paw is currently in slap animation (to prevent re-trigger)
        self._left_paw_active = False
        self._right_paw_active = False
        self._both_paws_active = False
        
        logger.info(f"Reaction system initialized with mode: {self.mode.value}")
    
    def set_mode(self, mode: str) -> None:
        """Set the input mode.
        
        Args:
            mode: Input mode ("kbm" or "controller")
        """
        mode_lower = mode.lower()
        if mode_lower in ("kbm", "controller"):
            self.mode = InputMode(mode_lower)
            logger.info(f"Mode changed to: {self.mode.value}")
            
            if self.on_mode_change:
                try:
                    self.on_mode_change(self.mode.value)
                except Exception as e:
                    logger.error(f"Error in on_mode_change callback: {e}")
        else:
            logger.warning(f"Invalid mode '{mode}', keeping current mode: {self.mode.value}")
    
    def get_mode(self) -> str:
        """Get the current input mode.
        
        Returns:
            Current mode as string ("kbm" or "controller")
        """
        return self.mode.value
    
    def on_input(self, source: str, detail: str) -> None:
        """Handle input event from InputManager.
        
        Routes input to appropriate reaction based on current mode.
        
        Args:
            source: Input source ("keyboard", "mouse_button", "mouse_scroll", or "joystick")
            detail: Input detail (key name, button name, etc.)
        """
        if self.mode == InputMode.KBM:
            self._handle_kbm_input(source, detail)
        else:  # JOYSTICK mode
            self._handle_joystick_input(source, detail)
    
    def _handle_kbm_input(self, source: str, detail: str) -> None:
        """Handle input in KBM mode.
        
        Keyboard input → left paw slap
        Mouse button/scroll → right paw slap
        
        Args:
            source: Input source
            detail: Input detail
        """
        if source == "keyboard":
            self._trigger_left_paw_slap()
        elif source in ("mouse_button", "mouse_scroll"):
            self._trigger_right_paw_slap()
        # Ignore joystick input in KBM mode
    
    def _handle_joystick_input(self, source: str, detail: str) -> None:
        """Handle input in JOYSTICK mode.
        
        Any joystick input → both paws down
        Ignores keyboard and mouse input
        
        Args:
            source: Input source
            detail: Input detail
        """
        if source == "joystick":
            # Track pressed joystick buttons for visual integration
            if "_button" in detail:
                # This is a button press - add to tracked set
                # Note: InputManager only fires on rising edge, so we add here
                # The overlay window can use this set for visual feedback
                self.pressed_joystick_buttons.add(detail)
            
            self._trigger_both_paws_down()
        # Ignore keyboard and mouse input in JOYSTICK mode
    
    def _trigger_left_paw_slap(self) -> None:
        """Trigger left paw slap animation with debounce."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check debounce
        if current_time - self._last_left_slap_time < self.DEBOUNCE_MS:
            return
        
        # Check if already active (prevent re-trigger)
        if self._left_paw_active:
            return
        
        # Update timing
        self._last_left_slap_time = current_time
        self._left_paw_active = True
        
        # Trigger slap
        if self.left_paw_slap_callback:
            try:
                self.left_paw_slap_callback()
            except Exception as e:
                logger.error(f"Error in left_paw_slap_callback: {e}")
        
        # Schedule return to idle
        # Note: In a real Qt app, this would use QTimer.singleShot
        # For now, we'll rely on the overlay to manage timing
        # The callback system allows the overlay to set its own timer
        
        logger.debug("Left paw slap triggered")
    
    def _trigger_right_paw_slap(self) -> None:
        """Trigger right paw slap animation with debounce."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check debounce
        if current_time - self._last_right_slap_time < self.DEBOUNCE_MS:
            return
        
        # Check if already active (prevent re-trigger)
        if self._right_paw_active:
            return
        
        # Update timing
        self._last_right_slap_time = current_time
        self._right_paw_active = True
        
        # Trigger slap
        if self.right_paw_slap_callback:
            try:
                self.right_paw_slap_callback()
            except Exception as e:
                logger.error(f"Error in right_paw_slap_callback: {e}")
        
        logger.debug("Right paw slap triggered")
    
    def _trigger_both_paws_down(self) -> None:
        """Trigger both paws down animation with debounce."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check debounce
        if current_time - self._last_both_slap_time < self.DEBOUNCE_MS:
            return
        
        # Check if already active (prevent re-trigger)
        if self._both_paws_active:
            return
        
        # Update timing
        self._last_both_slap_time = current_time
        self._both_paws_active = True
        
        # Trigger both paws
        if self.both_paws_down_callback:
            try:
                self.both_paws_down_callback()
            except Exception as e:
                logger.error(f"Error in both_paws_down_callback: {e}")
        
        logger.debug("Both paws down triggered")
    
    def return_left_paw_to_idle(self) -> None:
        """Return left paw to idle position."""
        self._left_paw_active = False
        
        if self.left_paw_return_callback:
            try:
                self.left_paw_return_callback()
            except Exception as e:
                logger.error(f"Error in left_paw_return_callback: {e}")
        
        logger.debug("Left paw returned to idle")
    
    def return_right_paw_to_idle(self) -> None:
        """Return right paw to idle position."""
        self._right_paw_active = False
        
        if self.right_paw_return_callback:
            try:
                self.right_paw_return_callback()
            except Exception as e:
                logger.error(f"Error in right_paw_return_callback: {e}")
        
        logger.debug("Right paw returned to idle")
    
    def return_both_paws_to_idle(self) -> None:
        """Return both paws to idle position."""
        self._both_paws_active = False
        
        if self.both_paws_return_callback:
            try:
                self.both_paws_return_callback()
            except Exception as e:
                logger.error(f"Error in both_paws_return_callback: {e}")
        
        logger.debug("Both paws returned to idle")
    
    def reset_state(self) -> None:
        """Reset all paw states to idle."""
        self._left_paw_active = False
        self._right_paw_active = False
        self._both_paws_active = False
        self.pressed_joystick_buttons.clear()
        logger.debug("Reaction system state reset")
    
    def on_joystick_disconnect(self) -> None:
        """Handle joystick disconnect event.
        
        If currently in JOYSTICK mode, auto-switch to KBM mode.
        Called by InputManager when joystick is disconnected.
        """
        if self.mode == InputMode.JOYSTICK:
            logger.info("Controller disconnected, switching to KBM mode")
            self.set_mode("kbm")
            self.pressed_joystick_buttons.clear()
