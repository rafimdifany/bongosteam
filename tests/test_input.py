"""Tests for input tracking system."""

import time
from unittest.mock import Mock, patch, MagicMock
import pytest

from bongo_steam.input.keyboard_listener import KeyboardListener
from bongo_steam.input.mouse_listener import MouseListener
from bongo_steam.input.joystick_listener import JoystickListener
from bongo_steam.input.input_manager import InputManager


class TestKeyboardListener:
    """Tests for KeyboardListener."""

    def test_init(self):
        """Test KeyboardListener initialization."""
        callback = Mock()
        listener = KeyboardListener(callback)
        
        assert listener.callback == callback
        assert listener.active_keys == set()
        assert listener.listener is None
        assert not listener.is_running()

    def test_get_key_name_special_key(self):
        """Test key name conversion for special keys."""
        from pynput import keyboard
        
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # Test special keys
        assert listener._get_key_name(keyboard.Key.space) == "space"
        assert listener._get_key_name(keyboard.Key.shift) == "shift"
        assert listener._get_key_name(keyboard.Key.enter) == "enter"

    def test_get_key_name_char_key(self):
        """Test key name conversion for character keys."""
        from pynput import keyboard
        
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # Test character keys (KeyCode with char)
        key_a = keyboard.KeyCode.from_char('a')
        assert listener._get_key_name(key_a) == "a"
        
        key_upper = keyboard.KeyCode.from_char('A')
        assert listener._get_key_name(key_upper) == "a"  # Should lowercase

    def test_on_press_fires_callback(self):
        """Test that on_press fires callback on new key press."""
        from pynput import keyboard
        
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # Simulate key press
        listener.on_press(keyboard.Key.space)
        
        # Callback should be called
        callback.assert_called_once_with("keyboard", "space")
        
        # Key should be in active_keys
        assert "space" in listener.active_keys

    def test_on_press_debounce(self):
        """Test that on_press does not fire callback for held keys."""
        from pynput import keyboard
        
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # First press
        listener.on_press(keyboard.Key.space)
        assert callback.call_count == 1
        
        # Second press (held) should not fire
        listener.on_press(keyboard.Key.space)
        assert callback.call_count == 1

    def test_on_release(self):
        """Test that on_release removes key from active_keys."""
        from pynput import keyboard
        
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # Press and release
        listener.on_press(keyboard.Key.space)
        assert "space" in listener.active_keys
        
        listener.on_release(keyboard.Key.space)
        assert "space" not in listener.active_keys

    def test_start_stop(self):
        """Test start and stop lifecycle."""
        callback = Mock()
        listener = KeyboardListener(callback)
        
        # Start
        listener.start()
        assert listener.is_running()
        
        # Stop
        listener.stop()
        time.sleep(0.1)  # Allow thread to stop
        assert not listener.is_running()


class TestMouseListener:
    """Tests for MouseListener."""

    def test_init(self):
        """Test MouseListener initialization."""
        callback = Mock()
        listener = MouseListener(callback)
        
        assert listener.callback == callback
        assert listener.active_buttons == set()
        assert listener.last_scroll_time == 0.0
        assert listener.scroll_debounce_ms == 50.0
        assert listener.listener is None
        assert not listener.is_running()

    def test_get_button_name(self):
        """Test button name conversion."""
        from pynput import mouse
        
        callback = Mock()
        listener = MouseListener(callback)
        
        assert listener._get_button_name(mouse.Button.left) == "left"
        assert listener._get_button_name(mouse.Button.right) == "right"
        assert listener._get_button_name(mouse.Button.middle) == "middle"

    def test_on_click_fires_callback(self):
        """Test that on_click fires callback on button press."""
        from pynput import mouse
        
        callback = Mock()
        listener = MouseListener(callback)
        
        # Simulate click
        listener.on_click(100, 100, mouse.Button.left, True)
        
        # Callback should be called
        callback.assert_called_once_with("mouse_button", "left")
        
        # Button should be in active_buttons
        assert "left" in listener.active_buttons

    def test_on_click_debounce(self):
        """Test that on_click does not fire callback for held buttons."""
        from pynput import mouse
        
        callback = Mock()
        listener = MouseListener(callback)
        
        # First press
        listener.on_click(100, 100, mouse.Button.left, True)
        assert callback.call_count == 1
        
        # Second press (held) should not fire
        listener.on_click(100, 100, mouse.Button.left, True)
        assert callback.call_count == 1

    def test_on_click_release(self):
        """Test that on_click release removes button from active_buttons."""
        from pynput import mouse
        
        callback = Mock()
        listener = MouseListener(callback)
        
        # Press and release
        listener.on_click(100, 100, mouse.Button.left, True)
        assert "left" in listener.active_buttons
        
        listener.on_click(100, 100, mouse.Button.left, False)
        assert "left" not in listener.active_buttons

    def test_on_scroll_fires_callback(self):
        """Test that on_scroll fires callback with debounce."""
        callback = Mock()
        listener = MouseListener(callback)
        
        # Simulate scroll up
        listener.on_scroll(100, 100, 0, 1)
        
        # Callback should be called
        callback.assert_called_once_with("mouse_scroll", "up")
        
        # Last scroll time should be updated
        assert listener.last_scroll_time > 0

    def test_on_scroll_debounce(self):
        """Test that on_scroll respects debounce interval."""
        callback = Mock()
        listener = MouseListener(callback)
        
        # First scroll
        listener.on_scroll(100, 100, 0, 1)
        assert callback.call_count == 1
        
        # Immediate second scroll should be debounced
        listener.on_scroll(100, 100, 0, 1)
        assert callback.call_count == 1
        
        # Wait for debounce
        time.sleep(0.06)
        
        # Third scroll should fire
        listener.on_scroll(100, 100, 0, -1)
        assert callback.call_count == 2
        callback.assert_called_with("mouse_scroll", "down")

    def test_start_stop(self):
        """Test start and stop lifecycle."""
        callback = Mock()
        listener = MouseListener(callback)
        
        # Start
        listener.start()
        assert listener.is_running()
        
        # Stop
        listener.stop()
        time.sleep(0.1)  # Allow thread to stop
        assert not listener.is_running()


class TestJoystickListener:
    """Tests for JoystickListener."""

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', False)
    def test_init_no_pygame(self):
        """Test initialization when pygame not available."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        assert listener.callback == callback
        assert not listener.is_running()

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', True)
    @patch('bongo_steam.input.joystick_listener.pygame')
    def test_init_with_pygame(self, mock_pygame):
        """Test initialization with pygame available."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        assert listener.callback == callback
        assert listener.poll_interval_ms == 8.0
        assert listener.axis_deadzone == 0.3
        assert not listener.is_running()

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', False)
    def test_start_no_pygame(self):
        """Test start when pygame not available."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        # Should not raise, just return
        listener.start()
        assert not listener.is_running()

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', True)
    @patch('bongo_steam.input.joystick_listener.pygame')
    def test_start_stop(self, mock_pygame):
        """Test start and stop lifecycle."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        # Mock pygame joystick
        mock_pygame.joystick.get_count.return_value = 0
        
        # Start
        listener.start()
        time.sleep(0.1)  # Allow thread to start
        assert listener.is_running()
        
        # Stop
        listener.stop()
        time.sleep(0.2)  # Allow thread to stop
        assert not listener.is_running()

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', True)
    @patch('bongo_steam.input.joystick_listener.pygame')
    def test_poll_buttons(self, mock_pygame):
        """Test button polling with rising edge detection."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        # Mock joystick
        mock_joystick = MagicMock()
        mock_joystick.get_instance_id.return_value = 0
        mock_joystick.get_name.return_value = "Test Joystick"
        mock_joystick.get_numbuttons.return_value = 2
        mock_joystick.get_numaxes.return_value = 0
        mock_joystick.get_button.side_effect = [True, False]  # Button 0 pressed
        
        mock_pygame.joystick.Joystick.return_value = mock_joystick
        mock_pygame.joystick.get_count.return_value = 1
        
        # Manually add joystick
        listener.joysticks[0] = mock_joystick
        listener.pressed_buttons[0] = set()
        listener.active_axes[0] = set()
        listener.last_axes_values[0] = {}
        
        # Poll buttons
        listener._poll_joystick_buttons(0, mock_joystick)
        
        # Callback should be called for button 0 press
        callback.assert_called_once_with("joystick", "joy0_button0")

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', True)
    @patch('bongo_steam.input.joystick_listener.pygame')
    def test_poll_axes_deadzone(self, mock_pygame):
        """Test axis polling with deadzone handling."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        # Mock joystick
        mock_joystick = MagicMock()
        mock_joystick.get_instance_id.return_value = 0
        mock_joystick.get_name.return_value = "Test Joystick"
        mock_joystick.get_numbuttons.return_value = 0
        mock_joystick.get_numaxes.return_value = 1
        
        # Manually add joystick
        listener.joysticks[0] = mock_joystick
        listener.pressed_buttons[0] = set()
        listener.active_axes[0] = set()
        listener.last_axes_values[0] = {}
        
        # Test within deadzone (should not fire)
        mock_joystick.get_axis.return_value = 0.2  # < 0.3 deadzone
        listener._poll_joystick_axes(0, mock_joystick)
        assert callback.call_count == 0
        
        # Test outside deadzone (should fire)
        mock_joystick.get_axis.return_value = 0.8  # > 0.3 deadzone
        listener.last_axes_values[0] = {0: 0.0}  # Previous value in deadzone
        listener._poll_joystick_axes(0, mock_joystick)
        callback.assert_called_once_with("joystick", "joy0_axis0")


class TestInputManager:
    """Tests for InputManager."""

    def test_init(self):
        """Test InputManager initialization."""
        callback = Mock()
        manager = InputManager(callback)
        
        assert manager.callback == callback
        assert manager.keyboard_listener is not None
        assert manager.mouse_listener is not None
        assert manager.joystick_listener is not None
        assert not manager.is_running()

    def test_init_without_callback(self):
        """Test InputManager initialization without callback."""
        manager = InputManager()
        
        assert manager.callback is None
        assert manager.on_input is None

    def test_handle_input(self):
        """Test internal handler dispatches to callbacks."""
        callback = Mock()
        on_input = Mock()
        manager = InputManager(callback)
        manager.on_input = on_input
        
        # Handle input
        manager._handle_input("keyboard", "space")
        
        # Both callbacks should be called
        callback.assert_called_once_with("keyboard", "space")
        on_input.assert_called_once_with("keyboard", "space")

    def test_handle_input_exception_handling(self):
        """Test that exceptions in callbacks are caught."""
        def bad_callback(source, detail):
            raise ValueError("Test error")
        
        on_input = Mock()
        manager = InputManager(bad_callback)
        manager.on_input = on_input
        
        # Should not raise
        manager._handle_input("keyboard", "space")
        
        # on_input should still be called
        on_input.assert_called_once_with("keyboard", "space")

    def test_start_stop(self):
        """Test start and stop lifecycle."""
        manager = InputManager()
        
        # Start
        manager.start()
        time.sleep(0.1)  # Allow threads to start
        assert manager.is_running()
        
        # Stop
        manager.stop()
        time.sleep(0.2)  # Allow threads to stop
        assert not manager.is_running()

    def test_get_status(self):
        """Test get_status returns correct listener states."""
        manager = InputManager()
        
        # Initially all stopped
        status = manager.get_status()
        assert status == {
            'keyboard': False,
            'mouse': False,
            'joystick': False,
        }
        
        # Start manager
        manager.start()
        time.sleep(0.1)
        
        # Check status
        status = manager.get_status()
        assert status['keyboard'] is True
        assert status['mouse'] is True
        
        # Stop manager
        manager.stop()
        time.sleep(0.2)


class TestIntegration:
    """Integration tests for the input system."""

    def test_keyboard_listener_independence(self):
        """Test that keyboard listener works independently."""
        callback = Mock()
        listener = KeyboardListener(callback)
        
        listener.start()
        time.sleep(0.1)
        assert listener.is_running()
        
        listener.stop()
        time.sleep(0.1)
        assert not listener.is_running()

    def test_mouse_listener_independence(self):
        """Test that mouse listener works independently."""
        callback = Mock()
        listener = MouseListener(callback)
        
        listener.start()
        time.sleep(0.1)
        assert listener.is_running()
        
        listener.stop()
        time.sleep(0.1)
        assert not listener.is_running()

    @patch('bongo_steam.input.joystick_listener.PYGAME_AVAILABLE', True)
    @patch('bongo_steam.input.joystick_listener.pygame')
    def test_joystick_listener_independence(self, mock_pygame):
        """Test that joystick listener works independently."""
        callback = Mock()
        listener = JoystickListener(callback)
        
        mock_pygame.joystick.get_count.return_value = 0
        
        listener.start()
        time.sleep(0.1)
        assert listener.is_running()
        
        listener.stop()
        time.sleep(0.2)
        assert not listener.is_running()

    def test_input_manager_coordination(self):
        """Test that InputManager coordinates all listeners."""
        events = []
        
        def track_event(source, detail):
            events.append((source, detail))
        
        manager = InputManager(track_event)
        
        # Start all
        manager.start()
        time.sleep(0.1)
        assert manager.is_running()
        
        # All listeners should be running
        status = manager.get_status()
        assert status['keyboard'] is True
        assert status['mouse'] is True
        
        # Stop all
        manager.stop()
        time.sleep(0.2)
        assert not manager.is_running()
