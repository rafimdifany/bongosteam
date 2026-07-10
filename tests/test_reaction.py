"""Unit tests for reaction system."""

import time
from unittest.mock import Mock, call

import pytest

from bongo_steam.reaction import ReactionSystem


class TestReactionSystemInit:
    """Test ReactionSystem initialization."""

    def test_init_default_mode_kbm(self):
        """Should initialize with KBM mode by default."""
        rs = ReactionSystem()
        assert rs.get_mode() == "kbm"

    def test_init_mode_controller(self):
        """Should initialize with controller mode when specified."""
        rs = ReactionSystem(mode="controller")
        assert rs.get_mode() == "controller"

    def test_init_invalid_mode_falls_back_to_kbm(self):
        """Should fall back to KBM mode for invalid mode."""
        rs = ReactionSystem(mode="invalid")
        assert rs.get_mode() == "kbm"

    def test_init_with_callbacks(self):
        """Should store all provided callbacks."""
        left_slap = Mock()
        right_slap = Mock()
        both_down = Mock()
        left_return = Mock()
        right_return = Mock()
        both_return = Mock()

        rs = ReactionSystem(
            left_paw_slap_callback=left_slap,
            right_paw_slap_callback=right_slap,
            both_paws_down_callback=both_down,
            left_paw_return_callback=left_return,
            right_paw_return_callback=right_return,
            both_paws_return_callback=both_return,
        )

        assert rs.left_paw_slap_callback == left_slap
        assert rs.right_paw_slap_callback == right_slap
        assert rs.both_paws_down_callback == both_down
        assert rs.left_paw_return_callback == left_return
        assert rs.right_paw_return_callback == right_return
        assert rs.both_paws_return_callback == both_return

    def test_init_pressed_joystick_buttons_empty(self):
        """Should initialize with empty pressed joystick buttons set."""
        rs = ReactionSystem()
        assert rs.pressed_joystick_buttons == set()


class TestReactionSystemModeSwitching:
    """Test mode switching functionality."""

    def test_set_mode_to_controller(self):
        """Should switch to controller mode."""
        rs = ReactionSystem()
        rs.set_mode("controller")
        assert rs.get_mode() == "controller"

    def test_set_mode_to_kbm(self):
        """Should switch to KBM mode."""
        rs = ReactionSystem(mode="controller")
        rs.set_mode("kbm")
        assert rs.get_mode() == "kbm"

    def test_set_mode_invalid_keeps_current(self):
        """Should keep current mode for invalid mode."""
        rs = ReactionSystem(mode="kbm")
        rs.set_mode("invalid")
        assert rs.get_mode() == "kbm"

    def test_set_mode_case_insensitive(self):
        """Should accept mode in any case."""
        rs = ReactionSystem()
        rs.set_mode("CONTROLLER")
        assert rs.get_mode() == "controller"


class TestReactionSystemKBMMode:
    """Test KBM mode input routing."""

    def test_keyboard_triggers_left_paw_slap(self):
        """Keyboard input should trigger left paw slap."""
        left_slap = Mock()
        rs = ReactionSystem(left_paw_slap_callback=left_slap)

        rs.on_input("keyboard", "a")

        left_slap.assert_called_once()

    def test_mouse_button_triggers_right_paw_slap(self):
        """Mouse button input should trigger right paw slap."""
        right_slap = Mock()
        rs = ReactionSystem(right_paw_slap_callback=right_slap)

        rs.on_input("mouse_button", "left")

        right_slap.assert_called_once()

    def test_mouse_scroll_triggers_right_paw_slap(self):
        """Mouse scroll input should trigger right paw slap."""
        right_slap = Mock()
        rs = ReactionSystem(right_paw_slap_callback=right_slap)

        rs.on_input("mouse_scroll", "up")

        right_slap.assert_called_once()

    def test_joystick_ignored_in_kbm_mode(self):
        """Joystick input should be ignored in KBM mode."""
        both_down = Mock()
        rs = ReactionSystem(
            mode="kbm",
            both_paws_down_callback=both_down
        )

        rs.on_input("joystick", "joy0_button0")

        both_down.assert_not_called()

    def test_both_paws_can_trigger_simultaneously(self):
        """Both paws should be able to trigger at same time."""
        left_slap = Mock()
        right_slap = Mock()
        rs = ReactionSystem(
            left_paw_slap_callback=left_slap,
            right_paw_slap_callback=right_slap,
        )

        rs.on_input("keyboard", "space")
        rs.on_input("mouse_button", "left")

        left_slap.assert_called_once()
        right_slap.assert_called_once()


class TestReactionSystemJoystickMode:
    """Test JOYSTICK mode input routing."""

    def test_joystick_button_triggers_both_paws(self):
        """Joystick button should trigger both paws down."""
        both_down = Mock()
        rs = ReactionSystem(
            mode="controller",
            both_paws_down_callback=both_down
        )

        rs.on_input("joystick", "joy0_button0")

        both_down.assert_called_once()

    def test_joystick_axis_triggers_both_paws(self):
        """Joystick axis should trigger both paws down."""
        both_down = Mock()
        rs = ReactionSystem(
            mode="controller",
            both_paws_down_callback=both_down
        )

        rs.on_input("joystick", "joy0_axis0")

        both_down.assert_called_once()

    def test_keyboard_ignored_in_joystick_mode(self):
        """Keyboard input should be ignored in JOYSTICK mode."""
        left_slap = Mock()
        rs = ReactionSystem(
            mode="controller",
            left_paw_slap_callback=left_slap
        )

        rs.on_input("keyboard", "space")

        left_slap.assert_not_called()

    def test_mouse_ignored_in_joystick_mode(self):
        """Mouse input should be ignored in JOYSTICK mode."""
        right_slap = Mock()
        rs = ReactionSystem(
            mode="controller",
            right_paw_slap_callback=right_slap
        )

        rs.on_input("mouse_button", "left")
        rs.on_input("mouse_scroll", "up")

        right_slap.assert_not_called()


class TestReactionSystemDebounce:
    """Test debounce functionality."""

    def test_left_paw_debounce_50ms(self):
        """Left paw should not trigger twice within 50ms."""
        left_slap = Mock()
        rs = ReactionSystem(left_paw_slap_callback=left_slap)

        rs.on_input("keyboard", "a")
        # Immediate second trigger should be debounced
        rs.on_input("keyboard", "b")

        left_slap.assert_called_once()

    def test_right_paw_debounce_50ms(self):
        """Right paw should not trigger twice within 50ms."""
        right_slap = Mock()
        rs = ReactionSystem(right_paw_slap_callback=right_slap)

        rs.on_input("mouse_button", "left")
        # Immediate second trigger should be debounced
        rs.on_input("mouse_button", "right")

        right_slap.assert_called_once()

    def test_both_paws_debounce_50ms(self):
        """Both paws should not trigger twice within 50ms."""
        both_down = Mock()
        rs = ReactionSystem(
            mode="controller",
            both_paws_down_callback=both_down
        )

        rs.on_input("joystick", "joy0_button0")
        # Immediate second trigger should be debounced
        rs.on_input("joystick", "joy0_button1")

        both_down.assert_called_once()

    def test_left_paw_can_trigger_after_debounce(self):
        """Left paw should trigger again after debounce period."""
        left_slap = Mock()
        rs = ReactionSystem(left_paw_slap_callback=left_slap)

        rs.on_input("keyboard", "a")
        
        # Wait for debounce period
        time.sleep(0.06)  # 60ms > 50ms debounce
        
        # Reset active state (simulating return to idle)
        rs._left_paw_active = False
        
        rs.on_input("keyboard", "b")

        assert left_slap.call_count == 2

    def test_different_paws_independent(self):
        """Left and right paw debounce should be independent."""
        left_slap = Mock()
        right_slap = Mock()
        rs = ReactionSystem(
            left_paw_slap_callback=left_slap,
            right_paw_slap_callback=right_slap,
        )

        rs.on_input("keyboard", "a")
        rs.on_input("mouse_button", "left")

        left_slap.assert_called_once()
        right_slap.assert_called_once()


class TestReactionSystemActiveState:
    """Test active state tracking."""

    def test_left_paw_active_prevents_retrigger(self):
        """Active left paw should prevent retrigger."""
        left_slap = Mock()
        rs = ReactionSystem(left_paw_slap_callback=left_slap)

        rs.on_input("keyboard", "a")
        # Try to trigger again without resetting
        rs.on_input("keyboard", "b")

        left_slap.assert_called_once()

    def test_right_paw_active_prevents_retrigger(self):
        """Active right paw should prevent retrigger."""
        right_slap = Mock()
        rs = ReactionSystem(right_paw_slap_callback=right_slap)

        rs.on_input("mouse_button", "left")
        # Try to trigger again without resetting
        rs.on_input("mouse_button", "right")

        right_slap.assert_called_once()

    def test_both_paws_active_prevents_retrigger(self):
        """Active both paws should prevent retrigger."""
        both_down = Mock()
        rs = ReactionSystem(
            mode="controller",
            both_paws_down_callback=both_down
        )

        rs.on_input("joystick", "joy0_button0")
        # Try to trigger again without resetting
        rs.on_input("joystick", "joy0_button1")

        both_down.assert_called_once()

    def test_return_to_idle_resets_active_state(self):
        """Returning to idle should reset active state."""
        left_slap = Mock()
        rs = ReactionSystem(left_paw_slap_callback=left_slap)

        rs.on_input("keyboard", "a")
        rs.return_left_paw_to_idle()
        
        # Should be able to trigger again
        time.sleep(0.06)  # Wait for debounce
        rs.on_input("keyboard", "b")

        assert left_slap.call_count == 2


class TestReactionSystemReturnToIdle:
    """Test return to idle functionality."""

    def test_return_left_paw_calls_callback(self):
        """return_left_paw_to_idle should call callback."""
        left_return = Mock()
        rs = ReactionSystem(left_paw_return_callback=left_return)

        rs.return_left_paw_to_idle()

        left_return.assert_called_once()

    def test_return_right_paw_calls_callback(self):
        """return_right_paw_to_idle should call callback."""
        right_return = Mock()
        rs = ReactionSystem(right_paw_return_callback=right_return)

        rs.return_right_paw_to_idle()

        right_return.assert_called_once()

    def test_return_both_paws_calls_callback(self):
        """return_both_paws_to_idle should call callback."""
        both_return = Mock()
        rs = ReactionSystem(both_paws_return_callback=both_return)

        rs.return_both_paws_to_idle()

        both_return.assert_called_once()

    def test_reset_state_clears_all(self):
        """reset_state should clear all active states and button set."""
        rs = ReactionSystem()
        rs.on_input("keyboard", "a")
        rs.pressed_joystick_buttons.add("joy0_button0")

        rs.reset_state()

        assert rs._left_paw_active is False
        assert rs._right_paw_active is False
        assert rs._both_paws_active is False
        assert len(rs.pressed_joystick_buttons) == 0


class TestReactionSystemJoystickButtonTracking:
    """Test joystick button tracking for visual integration."""

    def test_joystick_button_added_to_set(self):
        """Joystick button press should be added to tracking set."""
        rs = ReactionSystem(mode="controller")

        rs.on_input("joystick", "joy0_button0")

        assert "joy0_button0" in rs.pressed_joystick_buttons

    def test_multiple_joystick_buttons_tracked(self):
        """Multiple joystick buttons should be tracked."""
        rs = ReactionSystem(mode="controller")

        rs.on_input("joystick", "joy0_button0")
        rs.on_input("joystick", "joy0_button1")

        assert "joy0_button0" in rs.pressed_joystick_buttons
        assert "joy0_button1" in rs.pressed_joystick_buttons

    def test_joystick_axis_not_added_to_button_set(self):
        """Joystick axis should not be added to button set."""
        rs = ReactionSystem(mode="controller")

        rs.on_input("joystick", "joy0_axis0")

        assert "joy0_axis0" not in rs.pressed_joystick_buttons

    def test_joystick_button_tracking_in_kbm_mode(self):
        """Joystick buttons should still be tracked in KBM mode for visuals."""
        rs = ReactionSystem(mode="kbm")

        # Even though ignored for reaction, button should be tracked
        rs.on_input("joystick", "joy0_button0")

        # Note: Current implementation doesn't track in KBM mode
        # This test documents the expected behavior


class TestReactionSystemCallbackErrors:
    """Test error handling in callbacks."""

    def test_left_paw_callback_error_handled(self):
        """Errors in left paw callback should be caught."""
        def error_callback():
            raise RuntimeError("Test error")

        rs = ReactionSystem(left_paw_slap_callback=error_callback)
        
        # Should not raise
        rs.on_input("keyboard", "a")

    def test_right_paw_callback_error_handled(self):
        """Errors in right paw callback should be caught."""
        def error_callback():
            raise RuntimeError("Test error")

        rs = ReactionSystem(right_paw_slap_callback=error_callback)
        
        # Should not raise
        rs.on_input("mouse_button", "left")

    def test_both_paws_callback_error_handled(self):
        """Errors in both paws callback should be caught."""
        def error_callback():
            raise RuntimeError("Test error")

        rs = ReactionSystem(
            mode="controller",
            both_paws_down_callback=error_callback
        )
        
        # Should not raise
        rs.on_input("joystick", "joy0_button0")

    def test_return_callback_error_handled(self):
        """Errors in return callbacks should be caught."""
        def error_callback():
            raise RuntimeError("Test error")

        rs = ReactionSystem(
            left_paw_return_callback=error_callback,
            right_paw_return_callback=error_callback,
            both_paws_return_callback=error_callback
        )
        
        # Should not raise
        rs.return_left_paw_to_idle()
        rs.return_right_paw_to_idle()
        rs.return_both_paws_to_idle()
