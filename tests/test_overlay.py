"""Unit tests for SkinManager and OverlayWindow."""

import json
import os
import sys
import tempfile
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

# Ensure QApplication exists before importing PyQt widgets
from PyQt5.QtWidgets import QApplication

# Create QApplication if it doesn't exist (required for QPixmap and widgets)
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from PyQt5.QtGui import QPixmap

from bongo_steam.models.skin_manager import Skin, SkinManager, SkinPose
from bongo_steam.ui.overlay_window import OverlayWindow


# === Fixtures ===


@pytest.fixture
def temp_skins_dir() -> Generator[str, None, None]:
    """Create a temporary directory with test skin structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create default skin folder
        default_skin_path = os.path.join(tmpdir, "default")
        os.makedirs(default_skin_path)

        # Create skin.json
        skin_manifest = {
            "name": "Test Skin",
            "author": "Test Author",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        manifest_path = os.path.join(default_skin_path, "skin.json")
        with open(manifest_path, "w") as f:
            json.dump(skin_manifest, f)

        # Create placeholder PNG images
        from PIL import Image

        for pose_name in ["idle", "left", "right"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(default_skin_path, f"{pose_name}.png"))

        yield tmpdir


@pytest.fixture
def skin_manager(temp_skins_dir: str) -> SkinManager:
    """Create a SkinManager instance with test skins."""
    return SkinManager(skins_dir=temp_skins_dir)


# === SkinManager Tests ===


class TestSkinManagerInit:
    """Tests for SkinManager initialization."""

    def test_init_with_custom_dir(self, temp_skins_dir: str) -> None:
        """Test initialization with custom skins directory."""
        manager = SkinManager(skins_dir=temp_skins_dir)
        assert manager.skins_dir == temp_skins_dir
        assert manager.current_skin is None
        assert len(manager.cached_pixmaps) == 0

    @patch("bongo_steam.models.skin_manager.resource_path")
    def test_init_with_default_dir(self, mock_resource_path: Mock) -> None:
        """Test initialization with default skins directory."""
        mock_resource_path.return_value = "/default/skins/path"
        manager = SkinManager()
        assert manager.skins_dir == "/default/skins/path"
        mock_resource_path.assert_called_once_with("assets/skins")


class TestListAvailableSkins:
    """Tests for listing available skins."""

    def test_list_skins_success(self, skin_manager: SkinManager) -> None:
        """Test listing skins from a valid directory."""
        skins = skin_manager.list_available_skins()
        assert "default" in skins
        assert len(skins) >= 1

    def test_list_skins_empty_dir(self) -> None:
        """Test listing skins from an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkinManager(skins_dir=tmpdir)
            skins = manager.list_available_skins()
            assert skins == []

    def test_list_skins_nonexistent_dir(self) -> None:
        """Test listing skins from a nonexistent directory."""
        manager = SkinManager(skins_dir="/nonexistent/path")
        skins = manager.list_available_skins()
        assert skins == []

    def test_list_skins_ignores_invalid_folders(self, temp_skins_dir: str) -> None:
        """Test that folders without skin.json are ignored."""
        invalid_path = os.path.join(temp_skins_dir, "invalid_skin")
        os.makedirs(invalid_path)

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "invalid_skin" not in skins

    def test_list_skins_validates_structure(self, temp_skins_dir: str) -> None:
        """Test that skins with invalid structure are filtered out."""
        invalid_skin_path = os.path.join(temp_skins_dir, "missing_field")
        os.makedirs(invalid_skin_path)

        invalid_manifest = {
            "name": "Missing Author",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(invalid_skin_path, "skin.json"), "w") as f:
            json.dump(invalid_manifest, f)

        from PIL import Image
        for pose_name in ["idle", "left", "right"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(invalid_skin_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_field" not in skins

    def test_list_skins_validates_poses(self, temp_skins_dir: str) -> None:
        """Test that skins missing required poses are filtered out."""
        missing_pose_path = os.path.join(temp_skins_dir, "missing_pose")
        os.makedirs(missing_pose_path)

        missing_pose_manifest = {
            "name": "Missing Right Pose",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(missing_pose_path, "skin.json"), "w") as f:
            json.dump(missing_pose_manifest, f)

        from PIL import Image
        for pose_name in ["idle", "left"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(missing_pose_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_pose" not in skins

    def test_list_skins_validates_images(self, temp_skins_dir: str) -> None:
        """Test that skins with missing image files are filtered out."""
        missing_img_path = os.path.join(temp_skins_dir, "missing_image")
        os.makedirs(missing_img_path)

        missing_img_manifest = {
            "name": "Missing Image",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(missing_img_path, "skin.json"), "w") as f:
            json.dump(missing_img_manifest, f)

        from PIL import Image
        for pose_name in ["idle", "left"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(missing_img_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_image" not in skins


class TestValidateSkinFolder:
    """Tests for skin folder validation."""

    def test_validate_valid_skin(self, skin_manager: SkinManager) -> None:
        """Test validation of a valid skin folder."""
        skin_path = os.path.join(skin_manager.skins_dir, "default")
        result = skin_manager.validate_skin_folder(skin_path)

        assert result is True

    def test_validate_missing_manifest(self, temp_skins_dir: str) -> None:
        """Test validation fails when skin.json is missing."""
        skin_path = os.path.join(temp_skins_dir, "no_manifest")
        os.makedirs(skin_path)

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.validate_skin_folder(skin_path)

        assert result is False

    def test_validate_invalid_json(self, temp_skins_dir: str) -> None:
        """Test validation fails when skin.json has invalid JSON."""
        skin_path = os.path.join(temp_skins_dir, "bad_json")
        os.makedirs(skin_path)

        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            f.write("{ invalid json }")

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.validate_skin_folder(skin_path)

        assert result is False

    def test_validate_missing_required_field(self, temp_skins_dir: str) -> None:
        """Test validation fails when required field is missing."""
        skin_path = os.path.join(temp_skins_dir, "no_name")
        os.makedirs(skin_path)

        manifest = {
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            json.dump(manifest, f)

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.validate_skin_folder(skin_path)

        assert result is False

    def test_validate_missing_pose(self, temp_skins_dir: str) -> None:
        """Test validation fails when a required pose is missing."""
        skin_path = os.path.join(temp_skins_dir, "no_left")
        os.makedirs(skin_path)

        manifest = {
            "name": "Test",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            json.dump(manifest, f)

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.validate_skin_folder(skin_path)

        assert result is False

    def test_validate_missing_image_file(self, temp_skins_dir: str) -> None:
        """Test validation fails when image file doesn't exist."""
        skin_path = os.path.join(temp_skins_dir, "no_image_file")
        os.makedirs(skin_path)

        manifest = {
            "name": "Test",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            json.dump(manifest, f)

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.validate_skin_folder(skin_path)

        assert result is False

    def test_list_skins_validates_structure(self, temp_skins_dir: str) -> None:
        """Test that skins with invalid structure are filtered out."""
        # Create a skin with missing required field
        invalid_skin_path = os.path.join(temp_skins_dir, "missing_field")
        os.makedirs(invalid_skin_path)

        invalid_manifest = {
            "name": "Missing Author",
            # Missing 'author' field
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(invalid_skin_path, "skin.json"), "w") as f:
            json.dump(invalid_manifest, f)

        # Create images for invalid skin
        from PIL import Image
        for pose_name in ["idle", "left", "right"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(invalid_skin_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_field" not in skins

    def test_list_skins_validates_poses(self, temp_skins_dir: str) -> None:
        """Test that skins missing required poses are filtered out."""
        # Create a skin missing a pose
        missing_pose_path = os.path.join(temp_skins_dir, "missing_pose")
        os.makedirs(missing_pose_path)

        missing_pose_manifest = {
            "name": "Missing Right Pose",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                # Missing 'right' pose
            },
        }
        with open(os.path.join(missing_pose_path, "skin.json"), "w") as f:
            json.dump(missing_pose_manifest, f)

        # Create images
        from PIL import Image
        for pose_name in ["idle", "left"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(missing_pose_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_pose" not in skins

    def test_list_skins_validates_images(self, temp_skins_dir: str) -> None:
        """Test that skins with missing image files are filtered out."""
        # Create a skin with manifest but missing image
        missing_img_path = os.path.join(temp_skins_dir, "missing_image")
        os.makedirs(missing_img_path)

        missing_img_manifest = {
            "name": "Missing Image",
            "author": "Test",
            "version": "1.0",
            "poses": {
                "idle": {"file": "idle.png", "width": 200, "height": 200},
                "left": {"file": "left.png", "width": 200, "height": 200},
                "right": {"file": "right.png", "width": 200, "height": 200},
            },
        }
        with open(os.path.join(missing_img_path, "skin.json"), "w") as f:
            json.dump(missing_img_manifest, f)

        # Only create idle and left images, not right
        from PIL import Image
        for pose_name in ["idle", "left"]:
            img = Image.new("RGB", (200, 200), (200, 200, 200))
            img.save(os.path.join(missing_img_path, f"{pose_name}.png"))

        manager = SkinManager(skins_dir=temp_skins_dir)
        skins = manager.list_available_skins()

        assert "default" in skins
        assert "missing_image" not in skins


class TestLoadSkin:
    """Tests for loading skins."""

    def test_load_skin_success(self, skin_manager: SkinManager) -> None:
        """Test successfully loading a skin."""
        result = skin_manager.load_skin("default")

        assert result is True
        assert skin_manager.current_skin is not None
        assert skin_manager.current_skin.name == "default"
        assert skin_manager.current_skin.display_name == "Test Skin"
        assert "idle" in skin_manager.cached_pixmaps
        assert "left" in skin_manager.cached_pixmaps
        assert "right" in skin_manager.cached_pixmaps

    def test_load_skin_not_found(self, skin_manager: SkinManager) -> None:
        """Test loading a non-existent skin falls back to default."""
        result = skin_manager.load_skin("nonexistent")

        assert result is True
        assert skin_manager.current_skin is not None
        assert skin_manager.current_skin.name == "default"

    def test_load_skin_missing_idle_pose(self, temp_skins_dir: str) -> None:
        """Test loading a skin without idle pose falls back to default."""
        skin_path = os.path.join(temp_skins_dir, "no_idle")
        os.makedirs(skin_path)

        manifest = {
            "name": "No Idle Skin",
            "author": "Test",
            "version": "1.0",
            "poses": {"left": {"file": "left.png", "width": 200, "height": 200}},
        }
        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            json.dump(manifest, f)

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.load_skin("no_idle")

        assert result is True
        assert manager.current_skin.name == "default"

    def test_load_skin_invalid_json(self, temp_skins_dir: str) -> None:
        """Test loading a skin with invalid JSON falls back to default."""
        skin_path = os.path.join(temp_skins_dir, "invalid_json")
        os.makedirs(skin_path)

        with open(os.path.join(skin_path, "skin.json"), "w") as f:
            f.write("not valid json {{{")

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.load_skin("invalid_json")

        assert result is True
        assert manager.current_skin.name == "default"

    def test_load_skin_fallback_to_default(self, temp_skins_dir: str) -> None:
        """Test that loading an invalid skin falls back to default."""
        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.load_skin("nonexistent_skin")

        assert result is True
        assert manager.current_skin is not None
        assert manager.current_skin.name == "default"

    def test_load_skin_no_fallback_when_default_fails(self, temp_skins_dir: str) -> None:
        """Test that no fallback occurs when default skin itself fails."""
        skin_path = os.path.join(temp_skins_dir, "default")
        manifest_path = os.path.join(skin_path, "skin.json")

        with open(manifest_path, "w") as f:
            f.write("invalid json")

        manager = SkinManager(skins_dir=temp_skins_dir)
        result = manager.load_skin("default")

        assert result is False
        assert manager.current_skin is None


class TestGetPixmap:
    """Tests for getting cached pixmaps."""

    def test_get_pixmap_idle(self, skin_manager: SkinManager) -> None:
        """Test getting idle pose pixmap."""
        skin_manager.load_skin("default")
        pixmap = skin_manager.get_idle_pixmap()

        assert pixmap is not None
        assert not pixmap.isNull()

    def test_get_pixmap_left(self, skin_manager: SkinManager) -> None:
        """Test getting left pose pixmap."""
        skin_manager.load_skin("default")
        pixmap = skin_manager.get_left_pixmap()

        assert pixmap is not None
        assert not pixmap.isNull()

    def test_get_pixmap_right(self, skin_manager: SkinManager) -> None:
        """Test getting right pose pixmap."""
        skin_manager.load_skin("default")
        pixmap = skin_manager.get_right_pixmap()

        assert pixmap is not None
        assert not pixmap.isNull()

    def test_get_pixmap_nonexistent(self, skin_manager: SkinManager) -> None:
        """Test getting a non-existent pose returns None."""
        skin_manager.load_skin("default")
        pixmap = skin_manager.get_pixmap("nonexistent")

        assert pixmap is None

    def test_get_pixmap_without_load(self, skin_manager: SkinManager) -> None:
        """Test getting pixmap without loading a skin."""
        pixmap = skin_manager.get_idle_pixmap()

        assert pixmap is None


class TestHasPose:
    """Tests for checking pose availability."""

    def test_has_pose_true(self, skin_manager: SkinManager) -> None:
        """Test checking for an existing pose."""
        skin_manager.load_skin("default")
        assert skin_manager.has_pose("idle") is True
        assert skin_manager.has_pose("left") is True
        assert skin_manager.has_pose("right") is True

    def test_has_pose_false(self, skin_manager: SkinManager) -> None:
        """Test checking for a non-existent pose."""
        skin_manager.load_skin("default")
        assert skin_manager.has_pose("nonexistent") is False


class TestGetSkinInfo:
    """Tests for getting skin information."""

    def test_get_skin_info_loaded(self, skin_manager: SkinManager) -> None:
        """Test getting info for a loaded skin."""
        skin_manager.load_skin("default")
        info = skin_manager.get_skin_info()

        assert info is not None
        assert info["name"] == "default"
        assert info["display_name"] == "Test Skin"
        assert info["author"] == "Test Author"
        assert info["version"] == "1.0"
        assert set(info["poses"]) == {"idle", "left", "right"}

    def test_get_skin_info_not_loaded(self, skin_manager: SkinManager) -> None:
        """Test getting info without a loaded skin."""
        info = skin_manager.get_skin_info()

        assert info is None


class TestGetCurrentSkinName:
    """Tests for getting current skin name."""

    def test_get_current_skin_name_loaded(self, skin_manager: SkinManager) -> None:
        """Test getting name of loaded skin."""
        skin_manager.load_skin("default")
        name = skin_manager.get_current_skin_name()

        assert name == "default"

    def test_get_current_skin_name_not_loaded(self, skin_manager: SkinManager) -> None:
        """Test getting name when no skin loaded."""
        name = skin_manager.get_current_skin_name()

        assert name is None


class TestReload:
    """Tests for reloading skins."""

    def test_reload_success(self, skin_manager: SkinManager) -> None:
        """Test reloading a loaded skin."""
        skin_manager.load_skin("default")
        initial_pixmaps = skin_manager.cached_pixmaps.copy()

        result = skin_manager.reload()

        assert result is True
        assert skin_manager.current_skin is not None
        assert skin_manager.current_skin.name == "default"
        assert len(skin_manager.cached_pixmaps) == 3

    def test_reload_without_loaded_skin(self, skin_manager: SkinManager) -> None:
        """Test reloading when no skin is loaded."""
        result = skin_manager.reload()

        assert result is False

    def test_reload_clears_cache(self, skin_manager: SkinManager) -> None:
        """Test that reload clears the pixmap cache."""
        skin_manager.load_skin("default")
        assert len(skin_manager.cached_pixmaps) == 3

        skin_manager.cached_pixmaps.clear()
        assert len(skin_manager.cached_pixmaps) == 0

        result = skin_manager.reload()
        assert result is True
        assert len(skin_manager.cached_pixmaps) == 3


# === Skin and SkinPose Tests ===


class TestSkinPose:
    """Tests for SkinPose dataclass."""

    def test_skin_pose_creation(self) -> None:
        """Test creating a SkinPose instance."""
        pose = SkinPose(
            name="idle", filename="idle.png", width=200, height=200
        )

        assert pose.name == "idle"
        assert pose.filename == "idle.png"
        assert pose.width == 200
        assert pose.height == 200

    def test_skin_pose_frozen(self) -> None:
        """Test that SkinPose is frozen (immutable)."""
        pose = SkinPose(
            name="idle", filename="idle.png", width=200, height=200
        )

        with pytest.raises(AttributeError):
            pose.name = "modified"  # type: ignore


class TestSkin:
    """Tests for Skin dataclass."""

    def test_skin_creation(self) -> None:
        """Test creating a Skin instance."""
        poses = {
            "idle": SkinPose("idle", "idle.png", 200, 200),
            "left": SkinPose("left", "left.png", 200, 200),
        }
        skin = Skin(
            name="test",
            display_name="Test Skin",
            author="Author",
            version="1.0",
            poses=poses,
            path="/path/to/skin",
        )

        assert skin.name == "test"
        assert skin.display_name == "Test Skin"
        assert skin.author == "Author"
        assert skin.version == "1.0"
        assert len(skin.poses) == 2
        assert skin.path == "/path/to/skin"


# === OverlayWindow Tests ===


class TestOverlayWindowInit:
    """Tests for OverlayWindow initialization."""

    def test_init_with_skin_manager(self, skin_manager: SkinManager) -> None:
        """Test initialization with a provided SkinManager."""
        window = OverlayWindow(skin_manager=skin_manager)

        assert window.skin_manager is skin_manager
        assert window.current_pose == "idle"
        assert window.animation_scale == 1.0

        window.close()

    @patch("bongo_steam.ui.overlay_window.SkinManager")
    def test_init_without_skin_manager(
        self, mock_skin_manager_class: Mock
    ) -> None:
        """Test initialization creates SkinManager if not provided."""
        mock_manager = MagicMock()
        mock_skin_manager_class.return_value = mock_manager

        window = OverlayWindow()
        assert window.skin_manager is mock_manager

        window.close()


class TestOverlayWindowPose:
    """Tests for pose management in OverlayWindow."""

    def test_set_pose_idle(self, skin_manager: SkinManager) -> None:
        """Test setting idle pose."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        result = window.set_pose("idle")

        assert result is True
        assert window.current_pose == "idle"

        window.close()

    def test_set_pose_left(self, skin_manager: SkinManager) -> None:
        """Test setting left pose."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        result = window.set_pose("left")

        assert result is True
        assert window.current_pose == "left"

        window.close()

    def test_set_pose_right(self, skin_manager: SkinManager) -> None:
        """Test setting right pose."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        result = window.set_pose("right")

        assert result is True
        assert window.current_pose == "right"

        window.close()

    def test_set_pose_nonexistent(self, skin_manager: SkinManager) -> None:
        """Test setting a non-existent pose."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        result = window.set_pose("nonexistent")

        assert result is False
        assert window.current_pose == "idle"  # Unchanged

        window.close()

    def test_return_to_idle(self, skin_manager: SkinManager) -> None:
        """Test returning to idle pose."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)
        window.set_pose("left")

        window.return_to_idle()

        assert window.current_pose == "idle"
        assert window.animation_scale == 1.0

        window.close()


class TestOverlayWindowAnimation:
    """Tests for idle animation."""

    def test_start_stop_animation(self, skin_manager: SkinManager) -> None:
        """Test starting and stopping animation."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        window.start_animation()
        assert window.animation_timer.isActive()

        window.stop_animation()
        assert not window.animation_timer.isActive()

        window.close()

    def test_animate_idle_updates_scale(self, skin_manager: SkinManager) -> None:
        """Test that idle animation updates scale."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        initial_scale = window.animation_scale
        window.animation_time = 1.0  # Advance time
        window._animate_idle()

        # Scale should change from 1.0
        # sin(1.0 * 2.0) * 0.02 ≈ 0.018
        expected = 1.0 + 0.018  # Approximate
        assert abs(window.animation_scale - expected) < 0.01

        window.close()


class TestOverlayWindowReactions:
    """Tests for reaction callbacks."""

    def test_trigger_left_paw_slap(self, skin_manager: SkinManager) -> None:
        """Test triggering left paw slap."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        mock_callback = Mock()
        window.left_paw_slap_callback = mock_callback

        window.trigger_left_paw_slap()

        assert window.current_pose == "left"
        mock_callback.assert_called_once()

        window.close()

    def test_trigger_right_paw_slap(self, skin_manager: SkinManager) -> None:
        """Test triggering right paw slap."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        mock_callback = Mock()
        window.right_paw_slap_callback = mock_callback

        window.trigger_right_paw_slap()

        assert window.current_pose == "right"
        mock_callback.assert_called_once()

        window.close()

    def test_trigger_both_paws_down(self, skin_manager: SkinManager) -> None:
        """Test triggering both paws down."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        mock_callback = Mock()
        window.both_paws_down_callback = mock_callback

        window.trigger_both_paws_down()

        # Currently uses idle pose
        assert window.current_pose == "idle"
        mock_callback.assert_called_once()

        window.close()

    def test_return_left_paw(self, skin_manager: SkinManager) -> None:
        """Test returning left paw to idle."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)
        window.set_pose("left")

        mock_callback = Mock()
        window.left_paw_return_callback = mock_callback

        window.return_left_paw()

        assert window.current_pose == "idle"
        mock_callback.assert_called_once()

        window.close()

    def test_return_right_paw(self, skin_manager: SkinManager) -> None:
        """Test returning right paw to idle."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)
        window.set_pose("right")

        mock_callback = Mock()
        window.right_paw_return_callback = mock_callback

        window.return_right_paw()

        assert window.current_pose == "idle"
        mock_callback.assert_called_once()

        window.close()

    def test_return_both_paws(self, skin_manager: SkinManager) -> None:
        """Test returning both paws to idle."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        mock_callback = Mock()
        window.both_paws_return_callback = mock_callback

        window.return_both_paws()

        assert window.current_pose == "idle"
        mock_callback.assert_called_once()

        window.close()

    def test_callback_error_handling(self, skin_manager: SkinManager) -> None:
        """Test that callback errors don't crash the window."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        # Set a callback that raises an exception
        window.left_paw_slap_callback = Mock(side_effect=RuntimeError("Test error"))

        # Should not raise
        window.trigger_left_paw_slap()

        assert window.current_pose == "left"

        window.close()


class TestOverlayWindowDragging:
    """Tests for window dragging functionality."""

    def test_drag_position_initialized(self, skin_manager: SkinManager) -> None:
        """Test that drag position is initialized to None."""
        skin_manager.load_skin("default")
        window = OverlayWindow(skin_manager=skin_manager)

        assert window._drag_position is None

        window.close()


# === Integration Tests ===


class TestIntegration:
    """Integration tests for SkinManager and OverlayWindow."""

    def test_full_workflow(self, skin_manager: SkinManager) -> None:
        """Test complete workflow: load skin, create window, trigger reactions."""
        # Load skin
        assert skin_manager.load_skin("default") is True

        # Create window
        window = OverlayWindow(skin_manager=skin_manager)

        # Verify initial state
        assert window.current_pose == "idle"
        assert skin_manager.has_pose("idle")
        assert skin_manager.has_pose("left")
        assert skin_manager.has_pose("right")

        # Trigger reactions
        window.trigger_left_paw_slap()
        assert window.current_pose == "left"

        window.return_to_idle()
        assert window.current_pose == "idle"

        window.trigger_right_paw_slap()
        assert window.current_pose == "right"

        window.return_to_idle()
        assert window.current_pose == "idle"

        window.close()

    def test_skin_manager_repr(self, skin_manager: SkinManager) -> None:
        """Test SkinManager string representation."""
        skin_manager.load_skin("default")
        repr_str = repr(skin_manager)

        assert "SkinManager" in repr_str
        assert "default" in repr_str
        assert "cached_pixmaps=3" in repr_str
