"""Skin management for loading and caching avatar skins."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from PyQt5.QtGui import QPixmap

from ..utils.resources import resource_path

logger = logging.getLogger("BongoSteam")


@dataclass(frozen=True)
class SkinPose:
    """Represents a single pose image within a skin.

    Attributes:
        name: Pose identifier (e.g., 'idle', 'left', 'right')
        filename: Image filename relative to skin folder
        width: Image width in pixels
        height: Image height in pixels
    """

    name: str
    filename: str
    width: int
    height: int


@dataclass
class Skin:
    """Represents a loaded skin with all its poses.

    Attributes:
        name: Skin name (folder name)
        display_name: Human-readable name from skin.json
        author: Skin creator name
        version: Skin version string
        poses: Dictionary mapping pose names to SkinPose objects
        path: Absolute path to skin folder
    """

    name: str
    display_name: str
    author: str
    version: str
    poses: Dict[str, SkinPose]
    path: str


class SkinManager:
    """Manages loading, caching, and switching between avatar skins.

    Skins are stored in `assets/skins/<name>/` folders, each containing:
    - skin.json: Manifest file with metadata and pose definitions
    - PNG images: One image per pose

    The manager caches loaded QPixmap objects to avoid redundant file I/O.

    Attributes:
        skins_dir: Absolute path to the skins directory
        current_skin: Currently loaded Skin object
        cached_pixmaps: Dictionary mapping pose names to QPixmap objects
    """

    SKINS_FOLDER = "assets/skins"
    SUPPORTED_POSES = {"idle", "left", "right"}

    def __init__(self, skins_dir: Optional[str] = None):
        """Initialize the skin manager.

        Args:
            skins_dir: Custom path to skins directory. If None, uses default location.
        """
        if skins_dir is None:
            self.skins_dir = resource_path(self.SKINS_FOLDER)
        else:
            self.skins_dir = skins_dir

        self.current_skin: Optional[Skin] = None
        self.cached_pixmaps: Dict[str, QPixmap] = {}

        logger.debug(f"SkinManager initialized with skins_dir: {self.skins_dir}")

    def validate_skin_folder(self, folder_path: str) -> bool:
        """Validate a skin folder structure.

        Checks:
        1. skin.json exists and is valid JSON
        2. Required fields: name, author, version, poses
        3. All 3 poses defined: idle, left, right
        4. All image files exist

        Args:
            folder_path: Absolute path to the skin folder

        Returns:
            True if skin is valid, False otherwise
        """
        manifest_path = os.path.join(folder_path, "skin.json")

        # Check manifest exists
        if not os.path.exists(manifest_path):
            logger.warning(f"Skin manifest not found: {manifest_path}")
            return False

        # Try to parse JSON
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Invalid skin.json at {folder_path}: {e}")
            return False

        # Check required fields
        required_fields = ["name", "author", "version", "poses"]
        for field in required_fields:
            if field not in manifest:
                logger.warning(f"Missing required field '{field}' in {manifest_path}")
                return False

        # Check all poses defined
        poses = manifest.get("poses", {})
        for pose_name in self.SUPPORTED_POSES:
            if pose_name not in poses:
                logger.warning(f"Missing pose '{pose_name}' in {manifest_path}")
                return False

            # Check pose has file field
            pose_data = poses[pose_name]
            if "file" not in pose_data:
                logger.warning(f"Missing 'file' field for pose '{pose_name}' in {manifest_path}")
                return False

        # Check all image files exist
        for pose_name, pose_data in poses.items():
            if pose_name not in self.SUPPORTED_POSES:
                continue

            image_file = pose_data.get("file")
            image_path = os.path.join(folder_path, image_file)

            if not os.path.exists(image_path):
                logger.warning(f"Image file not found: {image_path}")
                return False

        logger.debug(f"Skin folder validated successfully: {folder_path}")
        return True

    def list_available_skins(self) -> List[str]:
        """List all valid skin names from the skins directory.

        Only returns skins that pass validation (valid skin.json, all poses, all images).

        Returns:
            List of valid skin names (folder names).
        """
        skins: List[str] = []

        if not os.path.exists(self.skins_dir):
            logger.warning(f"Skins directory does not exist: {self.skins_dir}")
            return skins

        try:
            for entry in os.listdir(self.skins_dir):
                skin_path = os.path.join(self.skins_dir, entry)

                if os.path.isdir(skin_path):
                    if self.validate_skin_folder(skin_path):
                        skins.append(entry)

        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Error listing skins directory: {e}")
            return skins

        logger.debug(f"Found {len(skins)} valid skins: {skins}")
        return skins

    def load_skin(self, skin_name: str) -> bool:
        """Load a skin by name and cache its pose images.

        Args:
            skin_name: Name of the skin (folder name)

        Returns:
            True if skin loaded successfully, False otherwise
        """
        skin_path = os.path.join(self.skins_dir, skin_name)

        # Validate skin folder first
        if not self.validate_skin_folder(skin_path):
            logger.error(f"Skin '{skin_name}' failed validation")
            # Attempt to fallback to default skin if not already trying default
            if skin_name != "default":
                logger.info("Attempting to fallback to default skin")
                return self.load_skin("default")
            return False

        manifest_path = os.path.join(skin_path, "skin.json")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # Parse skin metadata
            display_name = manifest.get("name", skin_name)
            author = manifest.get("author", "Unknown")
            version = manifest.get("version", "1.0")

            # Parse poses
            poses: Dict[str, SkinPose] = {}
            poses_data = manifest.get("poses", {})

            for pose_name in self.SUPPORTED_POSES:
                if pose_name not in poses_data:
                    logger.warning(f"Missing pose '{pose_name}' in skin '{skin_name}'")
                    continue

                pose_data = poses_data[pose_name]
                pose = SkinPose(
                    name=pose_name,
                    filename=pose_data.get("file", f"{pose_name}.png"),
                    width=pose_data.get("width", 200),
                    height=pose_data.get("height", 200),
                )
                poses[pose_name] = pose

            # Verify at least idle pose exists
            if "idle" not in poses:
                logger.error(f"Skin '{skin_name}' missing required 'idle' pose")
                return False

            # Create Skin object
            self.current_skin = Skin(
                name=skin_name,
                display_name=display_name,
                author=author,
                version=version,
                poses=poses,
                path=skin_path,
            )

            # Clear and reload pixmap cache
            self.cached_pixmaps.clear()
            self._load_pixmaps()

            logger.info(
                f"Loaded skin '{skin_name}' ({display_name} v{version} by {author}) "
                f"with {len(poses)} poses"
            )
            return True

        except (IOError, OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading skin '{skin_name}': {e}")
            self.current_skin = None
            self.cached_pixmaps.clear()
            return False

    def _load_pixmaps(self) -> None:
        """Load all pose pixmaps for the current skin into cache."""
        if self.current_skin is None:
            logger.warning("No skin loaded, cannot load pixmaps")
            return

        for pose_name, pose in self.current_skin.poses.items():
            image_path = os.path.join(self.current_skin.path, pose.filename)

            if not os.path.exists(image_path):
                logger.warning(f"Image file not found: {image_path}")
                continue

            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                logger.warning(f"Failed to load image: {image_path}")
                continue

            self.cached_pixmaps[pose_name] = pixmap
            logger.debug(f"Cached pixmap for pose '{pose_name}': {image_path}")

    def get_pixmap(self, pose_name: str) -> Optional[QPixmap]:
        """Get a cached pixmap for a pose.

        Args:
            pose_name: Name of the pose (e.g., 'idle', 'left', 'right')

        Returns:
            QPixmap for the pose, or None if not loaded or doesn't exist
        """
        pixmap = self.cached_pixmaps.get(pose_name)

        if pixmap is None:
            logger.warning(f"Pixmap not found for pose '{pose_name}'")

        return pixmap

    def get_idle_pixmap(self) -> Optional[QPixmap]:
        """Get the idle pose pixmap.

        Returns:
            QPixmap for idle pose, or None if not loaded
        """
        return self.get_pixmap("idle")

    def get_left_pixmap(self) -> Optional[QPixmap]:
        """Get the left pose pixmap.

        Returns:
            QPixmap for left pose, or None if not loaded
        """
        return self.get_pixmap("left")

    def get_right_pixmap(self) -> Optional[QPixmap]:
        """Get the right pose pixmap.

        Returns:
            QPixmap for right pose, or None if not loaded
        """
        return self.get_pixmap("right")

    def has_pose(self, pose_name: str) -> bool:
        """Check if a pose exists and is loaded.

        Args:
            pose_name: Name of the pose

        Returns:
            True if pose exists in current skin and is cached
        """
        return pose_name in self.cached_pixmaps

    def get_skin_info(self) -> Optional[Dict[str, Union[str, List[str]]]]:
        """Get information about the currently loaded skin.

        Returns:
            Dictionary with skin metadata, or None if no skin loaded
        """
        if self.current_skin is None:
            return None

        return {
            "name": self.current_skin.name,
            "display_name": self.current_skin.display_name,
            "author": self.current_skin.author,
            "version": self.current_skin.version,
            "poses": list(self.current_skin.poses.keys()),
        }

    def get_current_skin_name(self) -> Optional[str]:
        """Get the name of the currently loaded skin.

        Returns:
            Skin name (folder name) or None if no skin loaded
        """
        return self.current_skin.name if self.current_skin else None

    def reload(self) -> bool:
        """Force reload the current skin, clearing the cache first.

        Returns:
            True if skin reloaded successfully, False otherwise
        """
        if self.current_skin is None:
            logger.warning("No skin loaded, cannot reload")
            return False

        skin_name = self.current_skin.name
        self.cached_pixmaps.clear()
        self.current_skin = None

        logger.info(f"Reloading skin: {skin_name}")
        return self.load_skin(skin_name)

    def __repr__(self) -> str:
        """Return string representation of SkinManager."""
        skin_name = self.current_skin.name if self.current_skin else "None"
        cached_count = len(self.cached_pixmaps)
        return f"SkinManager(current_skin='{skin_name}', cached_pixmaps={cached_count})"
