"""Tests for ConfigManager."""

import os
import tempfile
from pathlib import Path

import pytest

from bongo_steam.models.config import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_default_config_creation(self, tmp_path: Path) -> None:
        """Test that ConfigManager creates default config file."""
        config_file = tmp_path / "test-config.ini"
        config = ConfigManager(config_path=str(config_file))

        # Verify file was created
        assert config_file.exists()

        # Verify default values
        assert config.mode == "kbm"
        assert config.controller_type == "xbox"
        assert config.skin == "default"
        assert config.toggle_shortcut == "ctrl+shift+m"
        assert config.window_x == -1
        assert config.window_y == -1
        assert config.launch_count == 0

    def test_get_method(self, tmp_path: Path) -> None:
        """Test get method retrieves correct values."""
        config_file = tmp_path / "test-config.ini"
        config = ConfigManager(config_path=str(config_file))

        assert config.get("mode") == "kbm"
        assert config.get("controller_type") == "xbox"
        assert config.get("nonexistent", "default") == "default"

    def test_set_method_with_type_coercion(self, tmp_path: Path) -> None:
        """Test set method with type coercion."""
        config_file = tmp_path / "test-config.ini"
        config = ConfigManager(config_path=str(config_file))

        # Test string value
        config.set("mode", "controller")
        assert config.mode == "controller"

        # Test integer value (should convert string to int)
        config.set("window_x", "100")
        assert config.window_x == 100
        assert isinstance(config.window_x, int)

        # Test integer value directly
        config.set("launch_count", 42)
        assert config.launch_count == 42
        assert isinstance(config.launch_count, int)

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test that config persists across save and load."""
        config_file = tmp_path / "test-config.ini"

        # Create and modify config
        config1 = ConfigManager(config_path=str(config_file))
        config1.set("mode", "controller")
        config1.set("skin", "custom")
        config1.set("window_x", 200)

        # Load config in new instance
        config2 = ConfigManager(config_path=str(config_file))

        # Verify values persisted
        assert config2.mode == "controller"
        assert config2.skin == "custom"
        assert config2.window_x == 200

    def test_as_dict(self, tmp_path: Path) -> None:
        """Test as_dict returns correct dictionary."""
        config_file = tmp_path / "test-config.ini"
        config = ConfigManager(config_path=str(config_file))

        config_dict = config.as_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["mode"] == "kbm"
        assert config_dict["controller_type"] == "xbox"
        assert config_dict["skin"] == "default"
        assert "launch_count" in config_dict

    def test_invalid_config_fallback(self, tmp_path: Path) -> None:
        """Test that invalid config values fall back to defaults."""
        config_file = tmp_path / "test-config.ini"

        # Write invalid config
        config_file.write_text("[Settings]\nmode = \nwindow_x = invalid\n")

        # Load should not crash and use defaults
        config = ConfigManager(config_path=str(config_file))

        # Invalid values should fall back to defaults
        assert config.mode == "kbm"  # Empty string falls back to default
        assert config.window_x == -1  # Invalid int falls back to default
