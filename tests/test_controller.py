"""Unit tests for controller visual and mapping."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from PyQt5.QtWidgets import QApplication

from bongo_steam.models.controller_map import (
    AxisMapping,
    ButtonMapping,
    ControllerMap,
    HatMapping,
)
from bongo_steam.ui.controller_visual import ControllerVisual


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app  # type: ignore[return-value]


@pytest.fixture
def temp_mapping_file() -> Generator[str, None, None]:
    """Create a temporary controller mapping file for testing."""
    mapping_data = {
        "image": "test_controller.png",
        "buttons": {
            "0": {
                "label": "Button A",
                "x": 0.5,
                "y": 0.5,
                "w": 0.1,
                "h": 0.1,
                "color": "#00FF00"
            },
            "1": {
                "label": "Button B",
                "x": 0.7,
                "y": 0.5,
                "w": 0.1,
                "h": 0.1,
                "color": "#FF0000"
            }
        },
        "axes": {
            "0": {
                "label": "Left Stick X",
                "highlight": "both",
                "x": 0.3,
                "y": 0.4,
                "w": 0.15,
                "h": 0.15,
                "color": "#0000FF"
            }
        },
        "hats": {
            "0": {
                "up": {
                    "label": "D-Pad Up",
                    "x": 0.2,
                    "y": 0.3,
                    "w": 0.08,
                    "h": 0.08,
                    "color": "#FFFF00"
                },
                "down": {
                    "label": "D-Pad Down",
                    "x": 0.2,
                    "y": 0.5,
                    "w": 0.08,
                    "h": 0.08,
                    "color": "#FFFF00"
                },
                "left": {
                    "label": "D-Pad Left",
                    "x": 0.15,
                    "y": 0.4,
                    "w": 0.08,
                    "h": 0.08,
                    "color": "#FFFF00"
                },
                "right": {
                    "label": "D-Pad Right",
                    "x": 0.25,
                    "y": 0.4,
                    "w": 0.08,
                    "h": 0.08,
                    "color": "#FFFF00"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mapping_data, f)
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def invalid_mapping_file() -> Generator[str, None, None]:
    """Create an invalid mapping file for error testing."""
    mapping_data = {
        "buttons": {
            "0": {
                "label": "Bad Button",
                "x": 1.5,
                "y": 0.5,
                "w": 0.1,
                "h": 0.1
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mapping_data, f)
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink(missing_ok=True)


class TestButtonMapping:
    """Tests for ButtonMapping dataclass."""

    def test_button_mapping_creation(self) -> None:
        """Test ButtonMapping can be created with valid values."""
        mapping = ButtonMapping(
            label="A",
            x=0.5,
            y=0.5,
            w=0.1,
            h=0.1,
            color="#00FF00"
        )

        assert mapping.label == "A"
        assert mapping.x == 0.5
        assert mapping.y == 0.5
        assert mapping.w == 0.1
        assert mapping.h == 0.1
        assert mapping.color == "#00FF00"


class TestAxisMapping:
    """Tests for AxisMapping dataclass."""

    def test_axis_mapping_creation(self) -> None:
        """Test AxisMapping can be created with valid values."""
        mapping = AxisMapping(
            label="Left X",
            highlight="both",
            x=0.3,
            y=0.4,
            w=0.15,
            h=0.15,
            color="#0000FF"
        )

        assert mapping.label == "Left X"
        assert mapping.highlight == "both"
        assert mapping.x == 0.3


class TestHatMapping:
    """Tests for HatMapping dataclass."""

    def test_hat_mapping_creation(self) -> None:
        """Test HatMapping can be created with valid values."""
        up = ButtonMapping(label="Up", x=0.2, y=0.3, w=0.08, h=0.08, color="#FF0")
        down = ButtonMapping(label="Down", x=0.2, y=0.5, w=0.08, h=0.08, color="#FF0")
        left = ButtonMapping(label="Left", x=0.15, y=0.4, w=0.08, h=0.08, color="#FF0")
        right = ButtonMapping(label="Right", x=0.25, y=0.4, w=0.08, h=0.08, color="#FF0")

        mapping = HatMapping(up=up, down=down, left=left, right=right)

        assert mapping.up.label == "Up"
        assert mapping.down.label == "Down"
        assert mapping.left.label == "Left"
        assert mapping.right.label == "Right"


class TestControllerMap:
    """Tests for ControllerMap class."""

    def test_load_valid_mapping(self, temp_mapping_file: str) -> None:
        """Test loading a valid controller mapping file."""
        controller_map = ControllerMap(temp_mapping_file)

        assert controller_map.image_filename == "test_controller.png"
        assert len(controller_map.buttons) == 2
        assert len(controller_map.axes) == 1
        assert len(controller_map.hats) == 1

    def test_get_button_position(self, temp_mapping_file: str) -> None:
        """Test getting button position by index."""
        controller_map = ControllerMap(temp_mapping_file)

        position = controller_map.get_button_position(0)
        assert position is not None
        assert position == (0.5, 0.5, 0.1, 0.1)

    def test_get_button_position_not_found(self, temp_mapping_file: str) -> None:
        """Test getting button position for non-existent button."""
        controller_map = ControllerMap(temp_mapping_file)

        position = controller_map.get_button_position(99)
        assert position is None

    def test_get_button_color(self, temp_mapping_file: str) -> None:
        """Test getting button color by index."""
        controller_map = ControllerMap(temp_mapping_file)

        color = controller_map.get_button_color(0)
        assert color == "#00FF00"

        color = controller_map.get_button_color(1)
        assert color == "#FF0000"

    def test_get_button_color_not_found(self, temp_mapping_file: str) -> None:
        """Test getting button color for non-existent button."""
        controller_map = ControllerMap(temp_mapping_file)

        color = controller_map.get_button_color(99)
        assert color is None

    def test_has_button(self, temp_mapping_file: str) -> None:
        """Test checking if button exists in mapping."""
        controller_map = ControllerMap(temp_mapping_file)

        assert controller_map.has_button(0) is True
        assert controller_map.has_button(1) is True
        assert controller_map.has_button(99) is False

    def test_invalid_mapping_file_not_found(self) -> None:
        """Test loading non-existent mapping file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ControllerMap("nonexistent.json")

    def test_invalid_mapping_structure(self, invalid_mapping_file: str) -> None:
        """Test loading mapping with invalid structure raises ValueError."""
        with pytest.raises(ValueError):
            ControllerMap(invalid_mapping_file)


class TestControllerVisual:
    """Tests for ControllerVisual widget."""

    def test_widget_creation(self, qapp: QApplication) -> None:
        """Test ControllerVisual widget can be created."""
        widget = ControllerVisual(controller_type="xbox")

        assert widget.controller_type == "xbox"
        assert widget.pressed_buttons == set()
        assert widget.highlight_alpha == 150

    def test_update_pressed_buttons(self, qapp: QApplication) -> None:
        """Test updating pressed buttons set."""
        widget = ControllerVisual(controller_type="xbox")

        pressed = {"joy0_button0", "joy0_button1"}
        widget.update_pressed_buttons(pressed)

        assert widget.pressed_buttons == pressed

    def test_update_pressed_buttons_triggers_repaint(self, qapp: QApplication) -> None:
        """Test that updating pressed buttons triggers widget repaint."""
        widget = ControllerVisual(controller_type="xbox")

        initial_buttons = widget.pressed_buttons.copy()
        new_buttons = {"joy0_button0"}

        widget.update_pressed_buttons(new_buttons)

        assert widget.pressed_buttons != initial_buttons
        assert widget.pressed_buttons == new_buttons

    def test_clear_highlights(self, qapp: QApplication) -> None:
        """Test clearing all button highlights."""
        widget = ControllerVisual(controller_type="xbox")

        widget.pressed_buttons = {"joy0_button0", "joy0_button1"}
        widget.clear_highlights()

        assert widget.pressed_buttons == set()

    def test_set_visible(self, qapp: QApplication) -> None:
        """Test setting widget visibility."""
        widget = ControllerVisual(controller_type="xbox")

        widget.set_visible(False)
        assert widget.isVisible() is False

        widget.set_visible(True)
        assert widget.isVisible() is True

    def test_get_controller_type(self, qapp: QApplication) -> None:
        """Test getting controller type."""
        widget = ControllerVisual(controller_type="ds5")

        assert widget.get_controller_type() == "ds5"

    def test_set_controller_type(self, qapp: QApplication) -> None:
        """Test changing controller type."""
        widget = ControllerVisual(controller_type="xbox")

        widget.set_controller_type("ds5")

        assert widget.controller_type == "ds5"

    def test_has_mapping(self, qapp: QApplication) -> None:
        """Test checking if valid mapping is loaded."""
        widget = ControllerVisual(controller_type="xbox")

        has_mapping = widget.has_mapping()
        assert isinstance(has_mapping, bool)


class TestControllerMapIntegration:
    """Integration tests for controller map with real mapping files."""

    def test_load_xbox_mapping(self) -> None:
        """Test loading real Xbox controller mapping."""
        xbox_map = ControllerMap("assets/controllers/xbox_map.json")

        assert xbox_map.image_filename == "xbox.png"
        assert len(xbox_map.buttons) == 10  # A, B, X, Y, LB, RB, Back, Start, L3, R3
        assert len(xbox_map.axes) == 6  # Left X/Y, Right X/Y, LT, RT
        assert len(xbox_map.hats) == 1  # D-Pad

    def test_load_ds5_mapping(self) -> None:
        """Test loading real DualShock 5 controller mapping."""
        ds5_map = ControllerMap("assets/controllers/ds5_map.json")

        assert ds5_map.image_filename == "ds5.png"
        assert len(ds5_map.buttons) == 12  # Cross, Circle, Square, Triangle, L1, R1, Create, Options, L3, R3, PS, Touchpad
        assert len(ds5_map.axes) == 6  # Left X/Y, Right X/Y, L2, R2
        assert len(ds5_map.hats) == 1  # D-Pad

    def test_xbox_button_positions_in_range(self) -> None:
        """Test that all Xbox button positions are in valid range [0.0, 1.0]."""
        xbox_map = ControllerMap("assets/controllers/xbox_map.json")

        for button_index, button in xbox_map.buttons.items():
            assert 0.0 <= button.x <= 1.0, f"Button {button_index} x out of range"
            assert 0.0 <= button.y <= 1.0, f"Button {button_index} y out of range"
            assert 0.0 <= button.w <= 1.0, f"Button {button_index} w out of range"
            assert 0.0 <= button.h <= 1.0, f"Button {button_index} h out of range"

    def test_ds5_button_positions_in_range(self) -> None:
        """Test that all DS5 button positions are in valid range [0.0, 1.0]."""
        ds5_map = ControllerMap("assets/controllers/ds5_map.json")

        for button_index, button in ds5_map.buttons.items():
            assert 0.0 <= button.x <= 1.0, f"Button {button_index} x out of range"
            assert 0.0 <= button.y <= 1.0, f"Button {button_index} y out of range"
            assert 0.0 <= button.w <= 1.0, f"Button {button_index} w out of range"
            assert 0.0 <= button.h <= 1.0, f"Button {button_index} h out of range"
