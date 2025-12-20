"""
Configuration management for ConvertImagesToWebP - MacAlpha v0.1

Handles all user settings with JSON persistence and defaults.
Cross-platform compatible (macOS primary, Windows/Linux secondary).
"""

import json
from pathlib import Path
from dataclasses import dataclass, fields, asdict
from typing import Tuple, Dict, Any, List
import platform


# Determine config directory based on OS
def get_config_dir() -> Path:
    """Get the appropriate config directory for the current OS."""
    if platform.system() == "Darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "ConvertImagesToWebP"
    elif platform.system() == "Windows":
        config_dir = Path.home() / "AppData" / "Local" / "ConvertImagesToWebP"
    else:  # Linux and others
        config_dir = Path.home() / ".config" / "ConvertImagesToWebP"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "settings.json"
PRESETS_DIR = CONFIG_DIR / "presets"


@dataclass
class AppConfig:
    """
    Application configuration settings.

    All settings are stored here for easy management and JSON serialization.
    """

    # Output settings
    OUTPUT_FOLDER: str = "WebP_Converted"

    # Supported file extensions
    EXTENSIONS: Tuple[str, ...] = (
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".ico", ".heic"
    )

    # Compression settings
    QUALITY: int = 90  # WebP quality (1-100)
    TARGET_MEGAPIXELS: float = 19.0  # Max resolution limit
    KEEP_METADATA: bool = True  # Preserve EXIF/ICC profiles
    WEBP_METHOD: int = 6  # Encoding method (1=fast, 6=best)

    # System settings
    MAX_THREADS: int = 8  # Max parallel threads

    # Square mode settings (mutually exclusive)
    ENABLE_CROP_SQUARE: bool = False  # Center-crop to 1:1
    ENABLE_SQUARE_CANVAS: bool = False  # Fit into 1:1 canvas
    CANVAS_FILL_MODE: str = "transparent"  # 'transparent' or 'color'
    CANVAS_FILL_COLOR: Tuple[int, int, int] = (255, 255, 255)  # RGB

    # UI preferences
    THEME: str = "dark"  # 'dark' or 'light'
    WINDOW_WIDTH: int = 600
    WINDOW_HEIGHT: int = 700

    # Recent folders (for quick access)
    RECENT_FOLDERS: List[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.RECENT_FOLDERS is None:
            self.RECENT_FOLDERS = []

    def validate(self) -> List[str]:
        """Validate configuration values."""
        errors = []

        if not 1 <= self.QUALITY <= 100:
            errors.append(f"QUALITY must be 1-100, got {self.QUALITY}")

        if not 0.1 <= self.TARGET_MEGAPIXELS <= 500.0:
            errors.append(f"TARGET_MEGAPIXELS must be 0.1-500, got {self.TARGET_MEGAPIXELS}")

        if not 1 <= self.WEBP_METHOD <= 6:
            errors.append(f"WEBP_METHOD must be 1-6, got {self.WEBP_METHOD}")

        if self.CANVAS_FILL_MODE not in ("transparent", "color"):
            errors.append(f"CANVAS_FILL_MODE must be 'transparent' or 'color'")

        if self.ENABLE_CROP_SQUARE and self.ENABLE_SQUARE_CANVAS:
            errors.append("ENABLE_CROP_SQUARE and ENABLE_SQUARE_CANVAS cannot both be True")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, tuple):
                data[field_info.name] = list(value)
            else:
                data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create config from dictionary."""
        valid_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}

        # Convert lists back to tuples
        if "EXTENSIONS" in filtered and isinstance(filtered["EXTENSIONS"], list):
            filtered["EXTENSIONS"] = tuple(filtered["EXTENSIONS"])
        if "CANVAS_FILL_COLOR" in filtered and isinstance(filtered["CANVAS_FILL_COLOR"], list):
            filtered["CANVAS_FILL_COLOR"] = tuple(filtered["CANVAS_FILL_COLOR"])

        return cls(**filtered)

    def save(self) -> None:
        """Save configuration to file."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from file, or return defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = cls.from_dict(data)
                errors = config.validate()
                if not errors:
                    return config
            except (json.JSONDecodeError, Exception):
                pass
        return cls()

    def add_recent_folder(self, folder: Path) -> None:
        """Add a folder to recent folders list."""
        folder_str = str(folder.resolve())

        # Remove if already exists
        if folder_str in self.RECENT_FOLDERS:
            self.RECENT_FOLDERS.remove(folder_str)

        # Add to front
        self.RECENT_FOLDERS.insert(0, folder_str)

        # Keep only last 10
        self.RECENT_FOLDERS = self.RECENT_FOLDERS[:10]

        self.save()


# Global config instance
config = AppConfig.load()
