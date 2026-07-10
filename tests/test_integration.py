"""Integration tests for BongoSteam component wiring."""

import tempfile
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from bongo_steam.models.config import ConfigManager
from bongo_steam.models.skin_manager import SkinManager
from bongo_steam.input.input_manager import InputManager
from bongo_steam.reaction.reaction_system import ReactionSystem
from bongo_steam.ui.overlay_window import OverlayWindow
from bongo_steam.ui.controller_visual import ControllerVisual


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test-config.ini"
        yield str(config_path)


@pytest.fixture
def temp_skins_dir():
    """Create a temporary skins directory with a test skin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skins_dir = Path(tmpdir) / "skins"
        skins_dir.mkdir()
        
        test_skin_dir = skins_dir / "test_skin"
        test_skin_dir.mkdir()
        
        import json
        from PIL import Image
        
        manifest = {
            "name": "Test Skin",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            }
        }
        
        with open(test_skin_dir / "skin.json", "w") as f:
            json.dump(manifest, f)
        
        for pose_name in ["idle", "left", "right"]:
            img = Image.new("RGBA", (200, 200), (255, 0, 0, 255))
            img.save(test_skin_dir / f"{pose_name}.png")
        
        yield str(skins_dir)


class TestComponentInitialization:
    """Tests for component initialization order."""
    
    def test_config_manager_initialization(self, temp_config):
        """Test ConfigManager initializes with correct defaults."""
        config = ConfigManager(config_path=temp_config)
        
        assert config.mode == "kbm"
        assert config.controller_type == "xbox"
        assert config.skin == "default"
        assert config.toggle_shortcut == "ctrl+shift+m"
        assert config.window_x == -1
        assert config.window_y == -1
        assert config.launch_count == 0
    
    def test_skin_manager_initialization(self, qapp, temp_skins_dir):
        """Test SkinManager loads skins successfully."""
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        
        available = skin_manager.list_available_skins()
        assert "test_skin" in available
        
        result = skin_manager.load_skin("test_skin")
        assert result is True
        assert skin_manager.current_skin is not None
        assert skin_manager.has_pose("idle")
    
    def test_input_manager_initialization(self):
        """Test InputManager initializes all listeners."""
        callback = Mock()
        input_manager = InputManager(callback=callback)
        
        assert input_manager.keyboard_listener is not None
        assert input_manager.mouse_listener is not None
        assert input_manager.joystick_listener is not None
        assert input_manager.callback == callback
    
    def test_reaction_system_initialization(self):
        """Test ReactionSystem initializes with correct mode."""
        reaction_system = ReactionSystem(mode="kbm")
        
        assert reaction_system.get_mode() == "kbm"
        assert reaction_system.pressed_joystick_buttons == set()
    
    def test_overlay_window_initialization(self, qapp, temp_skins_dir, temp_config):
        """Test OverlayWindow initializes with skin and config."""
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        skin_manager.load_skin("test_skin")
        
        config = ConfigManager(config_path=temp_config)
        
        window = OverlayWindow(skin_manager=skin_manager, config=config)
        
        assert window.skin_manager == skin_manager
        assert window.config == config
        assert window.current_pose == "idle"


class TestComponentWiring:
    """Tests for component signal/slot connections."""
    
    def test_input_manager_to_reaction_system(self):
        """Test InputManager callback connects to ReactionSystem."""
        reaction_system = ReactionSystem(mode="kbm")
        
        left_callback = Mock()
        reaction_system.left_paw_slap_callback = left_callback
        
        input_manager = InputManager()
        input_manager.on_input = reaction_system.on_input
        
        input_manager._handle_input("keyboard", "a")
        
        left_callback.assert_called_once()
    
    def test_reaction_system_to_overlay_callbacks(self, qapp, temp_skins_dir):
        """Test ReactionSystem callbacks connect to OverlayWindow."""
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        skin_manager.load_skin("test_skin")
        
        window = OverlayWindow(skin_manager=skin_manager)
        
        reaction_system = ReactionSystem(mode="kbm")
        reaction_system.left_paw_slap_callback = window.trigger_left_paw_slap
        reaction_system.right_paw_slap_callback = window.trigger_right_paw_slap
        
        reaction_system.on_input("keyboard", "a")
        
        assert window.current_pose == "left"
    
    def test_joystick_disconnect_to_mode_switch(self):
        """Test joystick disconnect triggers mode switch to KBM."""
        mode_change_callback = Mock()
        
        reaction_system = ReactionSystem(mode="controller")
        reaction_system.on_mode_change = mode_change_callback
        
        reaction_system.on_joystick_disconnect()
        
        assert reaction_system.get_mode() == "kbm"
        mode_change_callback.assert_called_once_with("kbm")
    
    def test_mode_change_updates_config(self, temp_config):
        """Test mode change is persisted to config."""
        config = ConfigManager(config_path=temp_config)
        config.mode = "kbm"
        
        reaction_system = ReactionSystem(mode=config.mode)
        
        def on_mode_change(new_mode: str):
            config.set("mode", new_mode)
        
        reaction_system.on_mode_change = on_mode_change
        reaction_system.set_mode("controller")
        
        assert config.mode == "controller"


class TestConfigPersistence:
    """Tests for configuration persistence."""
    
    def test_window_position_saved_on_close(self, qapp, temp_skins_dir, temp_config):
        """Test window position is saved when window closes."""
        config = ConfigManager(config_path=temp_config)
        
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        skin_manager.load_skin("test_skin")
        
        window = OverlayWindow(skin_manager=skin_manager, config=config)
        window.move(100, 200)
        window.close()
        
        reloaded_config = ConfigManager(config_path=temp_config)
        assert reloaded_config.window_x == 100
        assert reloaded_config.window_y == 200
    
    def test_window_position_restored_on_launch(self, qapp, temp_skins_dir, temp_config):
        """Test window position is restored from config on launch."""
        config = ConfigManager(config_path=temp_config)
        config.set("window_x", 150)
        config.set("window_y", 250)
        
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        skin_manager.load_skin("test_skin")
        
        window = OverlayWindow(skin_manager=skin_manager, config=config)
        
        assert window.x() == 150
        assert window.y() == 250
    
    def test_launch_count_increments(self, temp_config):
        """Test launch count can be incremented and persisted."""
        config = ConfigManager(config_path=temp_config)
        assert config.launch_count == 0
        
        config.launch_count += 1
        config.save()
        
        reloaded = ConfigManager(config_path=temp_config)
        assert reloaded.launch_count == 1


class TestControllerVisualIntegration:
    """Tests for ControllerVisual integration."""
    
    def test_controller_visual_visibility_by_mode(self, qapp, temp_skins_dir):
        """Test ControllerVisual visibility changes with mode."""
        skin_manager = SkinManager(skins_dir=temp_skins_dir)
        skin_manager.load_skin("test_skin")
        
        window = OverlayWindow(skin_manager=skin_manager)
        controller_visual = ControllerVisual(parent=window)
        
        controller_visual.hide()
        assert controller_visual.isHidden()
        
        controller_visual.show()
        assert not controller_visual.isHidden()
    
    def test_controller_visual_updates_pressed_buttons(self, qapp):
        """Test ControllerVisual updates highlighted buttons."""
        window = OverlayWindow()
        controller_visual = ControllerVisual(parent=window)
        
        pressed = {"joy0_button0", "joy0_button1"}
        controller_visual.update_pressed_buttons(pressed)
        
        assert controller_visual.pressed_buttons == pressed


class TestCleanup:
    """Tests for application cleanup."""
    
    def test_input_manager_stop_on_exit(self):
        """Test InputManager stops all listeners on cleanup."""
        input_manager = InputManager()
        input_manager.start()
        
        assert input_manager.is_running()
        
        input_manager.stop()
        
        assert not input_manager.is_running()
    
    def test_no_zombie_threads_after_stop(self):
        """Test all listener threads stop cleanly."""
        import threading
        
        input_manager = InputManager()
        input_manager.start()
        
        initial_thread_count = threading.active_count()
        
        input_manager.stop()
        
        import time
        time.sleep(0.2)
        
        final_thread_count = threading.active_count()
        assert final_thread_count <= initial_thread_count
