"""Controller button mapping model for visual feedback."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..utils.resources import resource_path

logger = logging.getLogger("BongoSteam")


@dataclass
class ButtonMapping:
    """Represents a single button mapping with position and visual properties.

    Attributes:
        label: Button label/name for display
        x: X position (relative 0.0-1.0)
        y: Y position (relative 0.0-1.0)
        w: Width (relative 0.0-1.0)
        h: Height (relative 0.0-1.0)
        color: Highlight color (hex string, e.g., "#FF0000")
    """

    label: str
    x: float
    y: float
    w: float
    h: float
    color: str


@dataclass
class AxisMapping:
    """Represents a single axis mapping with position and visual properties.

    Attributes:
        label: Axis label/name for display
        highlight: Direction to highlight ("positive", "negative", or "both")
        x: X position (relative 0.0-1.0)
        y: Y position (relative 0.0-1.0)
        w: Width (relative 0.0-1.0)
        h: Height (relative 0.0-1.0)
        color: Highlight color (hex string)
    """

    label: str
    highlight: str
    x: float
    y: float
    w: float
    h: float
    color: str


@dataclass
class HatMapping:
    """Represents a D-pad/hat mapping with directional positions.

    Attributes:
        up: Button mapping for up direction
        down: Button mapping for down direction
        left: Button mapping for left direction
        right: Button mapping for right direction
    """

    up: ButtonMapping
    down: ButtonMapping
    left: ButtonMapping
    right: ButtonMapping


class ControllerMap:
    """Loads and manages controller button position mappings.

    Loads JSON mapping files that define button positions as relative
    coordinates (0.0-1.0) for displaying visual feedback overlays.

    Attributes:
        image_filename: Filename of the controller image
        buttons: Dictionary mapping button index to ButtonMapping
        axes: Dictionary mapping axis index to AxisMapping
        hats: Dictionary mapping hat index to HatMapping
    """

    def __init__(self, mapping_path: str):
        """Initialize controller map from JSON file.

        Args:
            mapping_path: Path to the JSON mapping file

        Raises:
            FileNotFoundError: If mapping file doesn't exist
            ValueError: If mapping file has invalid structure
        """
        self.image_filename: str = ""
        self.buttons: Dict[int, ButtonMapping] = {}
        self.axes: Dict[int, AxisMapping] = {}
        self.hats: Dict[int, HatMapping] = {}

        self._load_mapping(mapping_path)
        logger.info(f"Loaded controller map from {mapping_path}")

    def _load_mapping(self, mapping_path: str) -> None:
        """Load and validate mapping from JSON file.

        Args:
            mapping_path: Path to the JSON mapping file

        Raises:
            FileNotFoundError: If mapping file doesn't exist
            ValueError: If mapping file has invalid structure
        """
        # Resolve resource path
        full_path = resource_path(mapping_path)

        if not Path(full_path).exists():
            raise FileNotFoundError(f"Controller mapping file not found: {full_path}")

        with open(full_path, "r") as f:
            data = json.load(f)

        # Validate and extract image filename
        if "image" not in data:
            raise ValueError("Mapping file missing required 'image' field")

        self.image_filename = data["image"]

        # Load buttons
        if "buttons" in data:
            self._load_buttons(data["buttons"])

        # Load axes
        if "axes" in data:
            self._load_axes(data["axes"])

        # Load hats
        if "hats" in data:
            self._load_hats(data["hats"])

        logger.debug(
            f"Loaded {len(self.buttons)} buttons, {len(self.axes)} axes, "
            f"{len(self.hats)} hats"
        )

    def _load_buttons(self, buttons_data: Dict[str, dict]) -> None:
        """Load button mappings from JSON data.

        Args:
            buttons_data: Dictionary of button index -> button data

        Raises:
            ValueError: If button data has invalid structure
        """
        for index_str, button_data in buttons_data.items():
            try:
                index = int(index_str)
                mapping = self._parse_button_mapping(button_data)
                self.buttons[index] = mapping
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid button mapping for index {index_str}: {e}")
                raise

    def _load_axes(self, axes_data: Dict[str, dict]) -> None:
        """Load axis mappings from JSON data.

        Args:
            axes_data: Dictionary of axis index -> axis data

        Raises:
            ValueError: If axis data has invalid structure
        """
        for index_str, axis_data in axes_data.items():
            try:
                index = int(index_str)
                mapping = self._parse_axis_mapping(axis_data)
                self.axes[index] = mapping
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid axis mapping for index {index_str}: {e}")
                raise

    def _load_hats(self, hats_data: Dict[str, dict]) -> None:
        """Load hat/d-pad mappings from JSON data.

        Args:
            hats_data: Dictionary of hat index -> hat data

        Raises:
            ValueError: If hat data has invalid structure
        """
        for index_str, hat_data in hats_data.items():
            try:
                index = int(index_str)
                mapping = self._parse_hat_mapping(hat_data)
                self.hats[index] = mapping
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid hat mapping for index {index_str}: {e}")
                raise

    def _parse_button_mapping(self, data: dict) -> ButtonMapping:
        """Parse button mapping from dictionary.

        Args:
            data: Dictionary with button mapping data

        Returns:
            ButtonMapping instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If coordinates are out of range
        """
        required_fields = ["label", "x", "y", "w", "h", "color"]
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Missing required field: {field}")

        # Validate coordinates are in range 0.0-1.0
        coords = {"x": data["x"], "y": data["y"], "w": data["w"], "h": data["h"]}
        for name, value in coords.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Coordinate {name}={value} out of range [0.0, 1.0]")

        return ButtonMapping(
            label=data["label"],
            x=data["x"],
            y=data["y"],
            w=data["w"],
            h=data["h"],
            color=data["color"],
        )

    def _parse_axis_mapping(self, data: dict) -> AxisMapping:
        """Parse axis mapping from dictionary.

        Args:
            data: Dictionary with axis mapping data

        Returns:
            AxisMapping instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If coordinates are out of range or highlight is invalid
        """
        required_fields = ["label", "highlight", "x", "y", "w", "h", "color"]
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Missing required field: {field}")

        # Validate coordinates
        coords = {"x": data["x"], "y": data["y"], "w": data["w"], "h": data["h"]}
        for name, value in coords.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Coordinate {name}={value} out of range [0.0, 1.0]")

        # Validate highlight direction
        valid_highlights = ["positive", "negative", "both"]
        if data["highlight"] not in valid_highlights:
            raise ValueError(
                f"Invalid highlight '{data['highlight']}', must be one of {valid_highlights}"
            )

        return AxisMapping(
            label=data["label"],
            highlight=data["highlight"],
            x=data["x"],
            y=data["y"],
            w=data["w"],
            h=data["h"],
            color=data["color"],
        )

    def _parse_hat_mapping(self, data: dict) -> HatMapping:
        """Parse hat/d-pad mapping from dictionary.

        Args:
            data: Dictionary with hat mapping data

        Returns:
            HatMapping instance

        Raises:
            KeyError: If required directions are missing
        """
        required_directions = ["up", "down", "left", "right"]
        for direction in required_directions:
            if direction not in data:
                raise KeyError(f"Missing required direction: {direction}")

        return HatMapping(
            up=self._parse_button_mapping(data["up"]),
            down=self._parse_button_mapping(data["down"]),
            left=self._parse_button_mapping(data["left"]),
            right=self._parse_button_mapping(data["right"]),
        )

    def get_button_position(
        self, button_index: int
    ) -> Optional[Tuple[float, float, float, float]]:
        """Get button position as (x, y, w, h) tuple.

        Args:
            button_index: Button index (0-based)

        Returns:
            Tuple of (x, y, w, h) relative coordinates, or None if not found
        """
        mapping = self.buttons.get(button_index)
        if mapping:
            return (mapping.x, mapping.y, mapping.w, mapping.h)
        return None

    def get_button_color(self, button_index: int) -> Optional[str]:
        """Get button highlight color.

        Args:
            button_index: Button index (0-based)

        Returns:
            Color hex string, or None if not found
        """
        mapping = self.buttons.get(button_index)
        if mapping:
            return mapping.color
        return None

    def get_image_path(self) -> str:
        """Get absolute path to controller image.

        Returns:
            Absolute path to controller image file
        """
        return resource_path(f"assets/controllers/{self.image_filename}")

    def has_button(self, button_index: int) -> bool:
        """Check if button index exists in mapping.

        Args:
            button_index: Button index to check

        Returns:
            True if button exists in mapping
        """
        return button_index in self.buttons
