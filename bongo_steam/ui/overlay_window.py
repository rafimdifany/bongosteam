"""Overlay window for displaying avatar on screen."""

import logging
import math
from typing import TYPE_CHECKING, Callable, Optional

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from ..models.config import ConfigManager

from ..models.skin_manager import SkinManager

logger = logging.getLogger("BongoSteam")


class OverlayWindow(QMainWindow):
    """Frameless, always-on-top overlay window for displaying the avatar.

    The window is transparent, positioned at the bottom-right corner,
    and supports dragging via mouse. It displays the avatar with an idle
    breathing animation and responds to input events via callbacks.

    Attributes:
        skin_manager: SkinManager instance for loading avatar images
        config: Optional ConfigManager for persisting window position
        current_pose: Current pose name ('idle', 'left', 'right')
        animation_scale: Current scale factor for idle animation
    """

    WINDOW_SIZE = 200
    MARGIN_FROM_EDGE = 20
    ANIMATION_INTERVAL_MS = 16  # ~60 FPS
    BREATHING_SPEED = 2.0  # Sine wave frequency
    BREATHING_AMPLITUDE = 0.02  # ±2% scale

    def __init__(
        self,
        skin_manager: Optional[SkinManager] = None,
        config: Optional["ConfigManager"] = None
    ):
        """Initialize the overlay window.

        Args:
            skin_manager: SkinManager instance. If None, creates a new one.
            config: ConfigManager for persisting window position.
        """
        super().__init__()

        self.skin_manager = skin_manager or SkinManager()
        self.config = config
        self.current_pose = "idle"
        self.animation_scale = 1.0
        self.animation_time = 0.0

        # Callbacks for reactions (set by ReactionSystem)
        self.left_paw_slap_callback: Optional[Callable[[], None]] = None
        self.right_paw_slap_callback: Optional[Callable[[], None]] = None
        self.both_paws_down_callback: Optional[Callable[[], None]] = None
        self.left_paw_return_callback: Optional[Callable[[], None]] = None
        self.right_paw_return_callback: Optional[Callable[[], None]] = None
        self.both_paws_return_callback: Optional[Callable[[], None]] = None

        # Drag tracking
        self._drag_position: Optional[QPoint] = None

        self._setup_window()
        self._setup_ui()
        self._setup_animation_timer()

        logger.debug("OverlayWindow initialized")

    def _setup_window(self) -> None:
        """Configure window flags and attributes."""
        # Window flags: frameless, always on top, tool window (no taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Fixed size
        self.setFixedSize(self.WINDOW_SIZE, self.WINDOW_SIZE)

        # Position at bottom-right corner
        self._position_bottom_right()

        # Set window title for debugging
        self.setWindowTitle("BongoSteam Overlay")

    def _position_bottom_right(self) -> None:
        """Position the window at saved position or bottom-right corner."""
        screen = self.screen()
        if screen is None:
            logger.warning("No screen available, using default position")
            return

        screen_geometry = screen.availableGeometry()

        if self.config and self.config.window_x >= 0 and self.config.window_y >= 0:
            x = self.config.window_x
            y = self.config.window_y
            
            x = max(screen_geometry.x(), min(x, screen_geometry.x() + screen_geometry.width() - self.WINDOW_SIZE))
            y = max(screen_geometry.y(), min(y, screen_geometry.y() + screen_geometry.height() - self.WINDOW_SIZE))
            
            logger.debug(f"Restored window position from config: ({x}, {y})")
        else:
            x = (
                screen_geometry.x()
                + screen_geometry.width()
                - self.WINDOW_SIZE
                - self.MARGIN_FROM_EDGE
            )
            y = (
                screen_geometry.y()
                + screen_geometry.height()
                - self.WINDOW_SIZE
                - self.MARGIN_FROM_EDGE
            )
            logger.debug(f"Window positioned at bottom-right: ({x}, {y})")

        self.move(x, y)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label for displaying avatar
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.avatar_label)

        # Load default skin
        if self.skin_manager.load_skin("default"):
            self._update_avatar_display()
        else:
            logger.warning("Failed to load default skin, using placeholder")

    def _setup_animation_timer(self) -> None:
        """Set up the idle animation timer."""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate_idle)
        self.animation_timer.setInterval(self.ANIMATION_INTERVAL_MS)

        logger.debug(f"Animation timer set to {self.ANIMATION_INTERVAL_MS}ms")

    def _animate_idle(self) -> None:
        """Update idle breathing animation.

        Uses sine wave for smooth breathing effect:
        scale = 1.0 + sin(time * speed) * amplitude
        """
        if self.current_pose != "idle":
            return

        # Update animation time
        self.animation_time += self.ANIMATION_INTERVAL_MS / 1000.0

        # Calculate scale using sine wave
        self.animation_scale = 1.0 + math.sin(
            self.animation_time * self.BREATHING_SPEED
        ) * self.BREATHING_AMPLITUDE

        # Update display
        self._update_avatar_display()

    def _update_avatar_display(self) -> None:
        """Update the avatar label with the current pose and scale."""
        # Get base pixmap
        pixmap = self.skin_manager.get_pixmap(self.current_pose)

        if pixmap is None or pixmap.isNull():
            logger.warning(f"No pixmap available for pose '{self.current_pose}'")
            return

        # Apply scale transform
        if self.current_pose == "idle" and self.animation_scale != 1.0:
            scaled_width = int(self.WINDOW_SIZE * self.animation_scale)
            scaled_height = int(self.WINDOW_SIZE * self.animation_scale)

            # Scale smoothly
            scaled_pixmap = pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.avatar_label.setPixmap(scaled_pixmap)
        else:
            # No scaling for non-idle poses
            self.avatar_label.setPixmap(pixmap)

    def start_animation(self) -> None:
        """Start the idle breathing animation."""
        self.animation_timer.start()
        logger.debug("Animation started")

    def stop_animation(self) -> None:
        """Stop the idle breathing animation."""
        self.animation_timer.stop()
        logger.debug("Animation stopped")

    def set_pose(self, pose_name: str) -> bool:
        """Set the current pose and update the display.

        Args:
            pose_name: Name of the pose ('idle', 'left', 'right')

        Returns:
            True if pose was set successfully, False otherwise
        """
        if not self.skin_manager.has_pose(pose_name):
            logger.warning(f"Pose '{pose_name}' not available in current skin")
            return False

        self.current_pose = pose_name
        self._update_avatar_display()
        logger.debug(f"Pose set to '{pose_name}'")
        return True

    def return_to_idle(self) -> None:
        """Return to idle pose and restart animation."""
        self.set_pose("idle")
        self.animation_scale = 1.0
        self._update_avatar_display()

    # === Reaction Callback Methods ===
    # These methods are called by ReactionSystem to trigger animations

    def trigger_left_paw_slap(self) -> None:
        """Trigger left paw slap animation."""
        self.stop_animation()
        self.set_pose("left")

        if self.left_paw_slap_callback:
            try:
                self.left_paw_slap_callback()
            except Exception as e:
                logger.error(f"Error in left_paw_slap_callback: {e}")

    def trigger_right_paw_slap(self) -> None:
        """Trigger right paw slap animation."""
        self.stop_animation()
        self.set_pose("right")

        if self.right_paw_slap_callback:
            try:
                self.right_paw_slap_callback()
            except Exception as e:
                logger.error(f"Error in right_paw_slap_callback: {e}")

    def trigger_both_paws_down(self) -> None:
        """Trigger both paws down animation (joystick mode)."""
        self.stop_animation()
        # For now, use idle pose for both paws down
        # TODO: Add dedicated 'both' pose when skin supports it
        self.set_pose("idle")

        if self.both_paws_down_callback:
            try:
                self.both_paws_down_callback()
            except Exception as e:
                logger.error(f"Error in both_paws_down_callback: {e}")

    def return_left_paw(self) -> None:
        """Return left paw to idle state."""
        self.return_to_idle()

        if self.left_paw_return_callback:
            try:
                self.left_paw_return_callback()
            except Exception as e:
                logger.error(f"Error in left_paw_return_callback: {e}")

    def return_right_paw(self) -> None:
        """Return right paw to idle state."""
        self.return_to_idle()

        if self.right_paw_return_callback:
            try:
                self.right_paw_return_callback()
            except Exception as e:
                logger.error(f"Error in right_paw_return_callback: {e}")

    def return_both_paws(self) -> None:
        """Return both paws to idle state."""
        self.return_to_idle()

        if self.both_paws_return_callback:
            try:
                self.both_paws_return_callback()
            except Exception as e:
                logger.error(f"Error in both_paws_return_callback: {e}")

    # === Mouse Event Handling for Dragging ===

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for window dragging.

        Args:
            event: QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Store the position for dragging
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            logger.debug(f"Drag started at position: {self._drag_position}")
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for window dragging.

        Args:
            event: QMouseEvent
        """
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_position is not None:
            # Move window to new position
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to stop dragging.

        Args:
            event: QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            logger.debug("Drag ended")
            event.accept()

    def showEvent(self, event) -> None:
        """Handle window show event.

        Args:
            event: QShowEvent
        """
        super().showEvent(event)
        # Start animation when window is shown
        self.start_animation()
        logger.debug("Window shown, animation started")

    def hideEvent(self, event) -> None:
        """Handle window hide event.

        Args:
            event: QHideEvent
        """
        super().hideEvent(event)
        # Stop animation when window is hidden
        self.stop_animation()
        logger.debug("Window hidden, animation stopped")

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Saves window position to config if available.

        Args:
            event: QCloseEvent
        """
        self.stop_animation()
        
        if self.config:
            self.config.set("window_x", self.x())
            self.config.set("window_y", self.y())
            logger.debug(f"Saved window position: ({self.x()}, {self.y()})")
        
        super().closeEvent(event)
        logger.debug("Window closed")
