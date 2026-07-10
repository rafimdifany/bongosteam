"""Resource path management for bundled and development environments."""

import os
import sys
from typing import Final


def resource_path(relative_path: str) -> str:
    """Get the absolute path to a resource.

    Handles both development (file system) and PyInstaller bundled environments.
    Special handling for bongo-steam.ini which goes to APPDATA directory.

    Args:
        relative_path: Relative path to the resource

    Returns:
        Absolute path to the resource as a string

    Examples:
        >>> resource_path("img/cat-rest.png")
        '/path/to/bongo_steam/img/cat-rest.png'

        >>> resource_path("bongo-steam.ini")
        'C:/Users/User/AppData/Roaming/bongo-steam.ini'  # Windows
        '/home/user/.config/bongo-steam.ini'  # Linux/Mac
    """
    if relative_path == "bongo-steam.ini":
        appdata = os.getenv("APPDATA")
        if appdata is None:
            # Fallback for non-Windows platforms
            appdata = os.path.expanduser("~/.config")
        return os.path.join(appdata, relative_path)

    if getattr(sys, 'frozen', False):
        # PyInstaller bundled executable
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    else:
        # Development mode - go up to project root
        # __file__ is bongo_steam/utils/resources.py
        # dirname(__file__) -> bongo_steam/utils
        # dirname(dirname(__file__)) -> bongo_steam
        # dirname(dirname(dirname(__file__))) -> project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)
