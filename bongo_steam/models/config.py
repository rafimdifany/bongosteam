"""Configuration management for BongoSteam application."""

import configparser
import logging
import os
from typing import Any, Dict, Optional

from ..utils.resources import resource_path

logger = logging.getLogger("BongoSteam")


class ConfigManager:
    """Manages application configuration using INI files.

    Handles loading, saving, and validating configuration values with
    sensible defaults and type coercion.

    Attributes:
        config_path: Path to the configuration file
        config: ConfigParser instance
        mode: Input mode ('kbm' or 'controller')
        controller_type: Controller type ('xbox', 'ps4', etc.)
        skin: Current skin name
        toggle_shortcut: Keyboard shortcut to toggle overlay
        window_x: X position of window (-1 = center on first launch)
        window_y: Y position of window (-1 = center on first launch)
        launch_count: Number of times the app has been launched
    """

    DEFAULT_CONFIG = {
        "Settings": {
            "mode": "kbm",
            "controller_type": "xbox",
            "skin": "default",
            "toggle_shortcut": "ctrl+shift+m",
            "window_x": "-1",
            "window_y": "-1",
            "launch_count": "0",
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            self.config_path = resource_path("bongo-steam.ini")
        else:
            self.config_path = config_path
        
        self.config = configparser.ConfigParser()

        # Initialize attributes with defaults
        self.mode = "kbm"
        self.controller_type = "xbox"
        self.skin = "default"
        self.toggle_shortcut = "ctrl+shift+m"
        self.window_x = -1
        self.window_y = -1
        self.launch_count = 0

        self.load()

    def load(self) -> None:
        """Load configuration from file or create with defaults."""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        else:
            self._load_existing_config()

        self._apply_config_values()

    def _create_default_config(self) -> None:
        """Create a new configuration file with default values."""
        self.config.read_dict(self.DEFAULT_CONFIG)
        try:
            with open(self.config_path, "w") as config_file:
                self.config.write(config_file)
            logger.info(f"Created default config at {self.config_path}")
        except (IOError, OSError) as e:
            logger.error(f"Error creating config file at {self.config_path}: {e}")
            self.config.read_dict(self.DEFAULT_CONFIG)

    def _load_existing_config(self) -> None:
        """Load existing configuration and merge with defaults."""
        try:
            self.config.read(self.config_path)

            # Merge defaults for any missing keys
            for section, values in self.DEFAULT_CONFIG.items():
                if section not in self.config:
                    self.config[section] = {}
                for key, value in values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value

            # Write back merged config
            with open(self.config_path, "w") as config_file:
                self.config.write(config_file)

        except (IOError, OSError, configparser.Error) as e:
            logger.error(f"Error reading config file from {self.config_path}: {e}")
            self.config.read_dict(self.DEFAULT_CONFIG)

    def _apply_config_values(self) -> None:
        """Apply loaded configuration values to instance attributes."""
        try:
            self.mode = self._safe_getstring("Settings", "mode", "kbm")
            self.controller_type = self._safe_getstring("Settings", "controller_type", "xbox")
            self.skin = self._safe_getstring("Settings", "skin", "default")
            self.toggle_shortcut = self._safe_getstring("Settings", "toggle_shortcut", "ctrl+shift+m")
            self.window_x = self._safe_getint("Settings", "window_x", -1)
            self.window_y = self._safe_getint("Settings", "window_y", -1)
            self.launch_count = max(0, self._safe_getint("Settings", "launch_count", 0))

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error loading settings: {e}")
            # Reset to defaults on error
            self._reset_to_defaults()

    def _reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.mode = "kbm"
        self.controller_type = "xbox"
        self.skin = "default"
        self.toggle_shortcut = "ctrl+shift+m"
        self.window_x = -1
        self.window_y = -1
        self.launch_count = 0

    def _safe_getboolean(self, section: str, key: str, default: bool = False) -> bool:
        """Safely get a boolean value from config.

        Args:
            section: Config section name
            key: Config key name
            default: Default value if parsing fails

        Returns:
            Boolean value from config or default
        """
        try:
            value = self.config.get(section, key, fallback=str(default)).lower()
            return value in ("true", "1", "yes", "on")
        except (ValueError, AttributeError):
            return default

    def _safe_getint(self, section: str, key: str, default: int = 0) -> int:
        """Safely get an integer value from config.

        Args:
            section: Config section name
            key: Config key name
            default: Default value if parsing fails

        Returns:
            Integer value from config or default
        """
        try:
            return int(self.config.get(section, key, fallback=str(default)))
        except (ValueError, TypeError):
            return default

    def _safe_getstring(self, section: str, key: str, default: str = "") -> str:
        """Safely get a string value from config.

        Args:
            section: Config section name
            key: Config key name
            default: Default value if parsing fails

        Returns:
            String value from config or default
        """
        try:
            value = self.config.get(section, key, fallback=default)
            # Return default if value is empty string
            return value if value else default
        except (ValueError, TypeError):
            return default

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            self.config["Settings"]["mode"] = self.mode
            self.config["Settings"]["controller_type"] = self.controller_type
            self.config["Settings"]["skin"] = self.skin
            self.config["Settings"]["toggle_shortcut"] = self.toggle_shortcut
            self.config["Settings"]["window_x"] = str(self.window_x)
            self.config["Settings"]["window_y"] = str(self.window_y)
            self.config["Settings"]["launch_count"] = str(self.launch_count)

            with open(self.config_path, "w") as config_file:
                self.config.write(config_file)

            logger.debug("Configuration saved successfully")

        except (IOError, OSError) as e:
            logger.error(f"Error saving config to {self.config_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by attribute name.

        Args:
            key: Attribute name
            default: Default value if attribute doesn't exist

        Returns:
            Configuration value or default

        Example:
            >>> config.get('mode', 'kbm')
            'kbm'
        """
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by attribute name with type coercion.

        Args:
            key: Attribute name
            value: Value to set

        Example:
            >>> config.set('mode', 'controller')
        """
        # Get the current attribute type if it exists
        current_value = getattr(self, key, None)
        if current_value is not None:
            # Type coercion based on current value type
            if isinstance(current_value, bool):
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes", "on")
                else:
                    value = bool(value)
            elif isinstance(current_value, int):
                value = int(value)
            # Strings remain as strings

        setattr(self, key, value)
        self.save()

    def as_dict(self) -> Dict[str, Any]:
        """Return configuration as a dictionary.

        Returns:
            Dictionary of configuration values

        Example:
            >>> config.as_dict()
            {'mode': 'kbm', 'controller_type': 'xbox', ...}
        """
        return {
            "mode": self.mode,
            "controller_type": self.controller_type,
            "skin": self.skin,
            "toggle_shortcut": self.toggle_shortcut,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "launch_count": self.launch_count,
        }

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return f"ConfigManager({self.as_dict()})"
