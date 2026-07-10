"""Controller visual overlay widget for displaying button highlights."""

import logging
import re
from typing import Optional, Set

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..models.controller_map import ControllerMap

logger = logging.getLogger("BongoSteam")


class ControllerVisual(QWidget):
    """Widget that displays a controller image with button highlights.

    Shows a controller image (Xbox or DualShock 5) in the background layer,
    with semi-transparent colored rectangles highlighting pressed buttons.

    The widget is only visible in joystick mode and updates dynamically
    based on the pressed_joystick_buttons set from ReactionSystem.

    Attributes:
        controller_map: ControllerMap instance with button position data
        controller_image: QPixmap of the controller image
        pressed_buttons: Set of pressed button identifiers (e.g., "joy0_button0")
        highlight_alpha: Alpha value for highlight rectangles (0-255)
    """

    HIGHLIGHT_ALPHA = 150  # Semi-transparent highlight
    DEFAULT_WIDTH = 400
    DEFAULT_HEIGHT = 300

    def __init__(
        self,
        controller_type: str = "xbox",
        parent: Optional[QWidget] = None
    ):
        """Initialize the controller visual widget.

        Args:
            controller_type: Controller type ("xbox" or "ds5")
            parent: Parent widget (should be OverlayWindow)
        """
        super().__init__(parent)

        self.controller_type = controller_type
        self.controller_map: Optional[ControllerMap] = None
        self.controller_image: Optional[QPixmap] = None
        self.pressed_buttons: Set[str] = set()
        self.highlight_alpha = self.HIGHLIGHT_ALPHA

        self._setup_ui()
        self._load_controller_map(controller_type)

        logger.debug(f"ControllerVisual initialized for {controller_type}")

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Configure widget properties
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create label for controller image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.image_label)

        # Set minimum size
        self.setMinimumSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    def _load_controller_map(self, controller_type: str) -> None:
        """Load controller mapping for the specified controller type.

        Args:
            controller_type: Controller type ("xbox" or "ds5")
        """
        # Determine mapping file path
        mapping_file = f"assets/controllers/{controller_type}_map.json"

        try:
            # Load controller map
            self.controller_map = ControllerMap(mapping_file)

            # Load controller image
            image_path = self.controller_map.get_image_path()
            self.controller_image = QPixmap(image_path)

            if self.controller_image.isNull():
                logger.error(f"Failed to load controller image: {image_path}")
            else:
                # Display the image
                self.image_label.setPixmap(self.controller_image)
                logger.debug(f"Loaded controller image: {image_path}")

        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load controller map: {e}")
            self.controller_map = None

    def set_controller_type(self, controller_type: str) -> None:
        """Change the controller type and reload mapping.

        Args:
            controller_type: Controller type ("xbox" or "ds5")
        """
        self.controller_type = controller_type
        self._load_controller_map(controller_type)
        self.update()  # Trigger repaint

    def update_pressed_buttons(self, pressed_buttons: Set[str]) -> None:
        """Update the set of pressed buttons and trigger repaint.

        Args:
            pressed_buttons: Set of pressed button identifiers
        """
        if self.pressed_buttons != pressed_buttons:
            self.pressed_buttons = pressed_buttons
            self.update()  # Trigger repaint
            logger.debug(f"Updated pressed buttons: {len(pressed_buttons)} buttons")

    def paintEvent(self, a0) -> None:
        """Override paint event to draw button highlights.

        Draws semi-transparent colored rectangles over pressed buttons
        on top of the controller image.

        Args:
            a0: QPaintEvent
        """
        super().paintEvent(a0)

        # Skip if no controller map or no pressed buttons
        if not self.controller_map or not self.pressed_buttons:
            return

        # Create painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get widget dimensions
        widget_width = self.width()
        widget_height = self.height()

        # Draw highlights for each pressed button
        for button_id in self.pressed_buttons:
            self._draw_button_highlight(painter, button_id, widget_width, widget_height)

        painter.end()

    def _draw_button_highlight(
        self, painter: QPainter, button_id: str, width: int, height: int
    ) -> None:
        """Draw highlight rectangle for a pressed button.

        Args:
            painter: QPainter instance
            button_id: Button identifier (e.g., "joy0_button0")
            width: Widget width in pixels
            height: Widget height in pixels
        """
        if not self.controller_map:
            return

        match = re.search(r"_button(\d+)", button_id)
        if not match:
            return

        button_index = int(match.group(1))

        position = self.controller_map.get_button_position(button_index)
        if not position:
            return

        x_rel, y_rel, w_rel, h_rel = position

        x = int(x_rel * width)
        y = int(y_rel * height)
        w = int(w_rel * width)
        h = int(h_rel * height)

        color_hex = self.controller_map.get_button_color(button_index)
        if not color_hex:
            color_hex = "#00FF00"

        color = QColor(color_hex)
        color.setAlpha(self.highlight_alpha)

        painter.fillRect(x, y, w, h, color)

        logger.debug(
            f"Drew highlight for button {button_index} at ({x}, {y}) "
            f"size ({w}x{h})"
        )

    def resizeEvent(self, a0) -> None:
        """Handle resize event to scale controller image.

        Args:
            a0: QResizeEvent
        """
        super().resizeEvent(a0)

        # Scale controller image to fit new size
        if self.controller_image and not self.controller_image.isNull():
            scaled_pixmap = self.controller_image.scaled(
                self.width(),
                self.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)

    def clear_highlights(self) -> None:
        """Clear all button highlights."""
        self.pressed_buttons.clear()
        self.update()

    def set_visible(self, visible: bool) -> None:
        """Set widget visibility.

        Args:
            visible: True to show widget, False to hide
        """
        self.setVisible(visible)
        logger.debug(f"ControllerVisual visibility set to {visible}")

    def get_controller_type(self) -> str:
        """Get the current controller type.

        Returns:
            Current controller type string
        """
        return self.controller_type

    def has_mapping(self) -> bool:
        """Check if a valid controller mapping is loaded.

        Returns:
            True if controller map is loaded and valid
        """
        return self.controller_map is not None and self.controller_image is not None
