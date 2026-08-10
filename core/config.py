"""Settings: dataclass + JSON persistence + presets.

One flat dataclass. No nesting, no schema layer — it is a settings file, not a
database.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

APP_NAME = "ConvertImagesToWebP"
VERSION = "2.0.0"

# Everything we will try to read. Availability of HEIC/AVIF decoding is probed
# at runtime in formats.py — this is just the filename filter.
SOURCE_EXTENSIONS: tuple[str, ...] = (
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
    ".webp", ".avif", ".heic", ".heif", ".gif", ".ico",
)

OUTPUT_FORMATS = ("webp", "avif", "jpeg", "png")
RESIZE_MODES = ("none", "long_edge", "width", "height", "megapixels")
SQUARE_MODES = ("off", "crop", "canvas")
DEST_MODES = ("subfolder", "custom", "in_place")
ON_EXISTING = ("skip", "overwrite", "rename")
THEMES = ("system", "light", "dark")


def config_dir() -> Path:
    # Override lets tests run without clobbering the real user's settings.
    override = os.environ.get("WEBP_STUDIO_CONFIG_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path

    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


CONFIG_FILE = config_dir() / "settings.json"


@dataclass
class Settings:
    # --- output ---------------------------------------------------------
    # Defaults deliberately equal the "Balanced" preset, so a fresh install
    # opens on a named preset instead of "Custom".
    output_format: str = "webp"
    quality: int = 85
    lossless: bool = False
    effort: int = 6              # webp `method` / avif `speed`, 0-6, higher = slower+smaller

    # --- geometry -------------------------------------------------------
    resize_mode: str = "none"
    resize_value: float = 2560.0  # px for long_edge/width/height, MP for megapixels
    square_mode: str = "off"
    canvas_fill: str = "transparent"  # "transparent" or "#rrggbb"

    # --- metadata -------------------------------------------------------
    keep_metadata: bool = True
    strip_gps: bool = False

    # --- destination ----------------------------------------------------
    dest_mode: str = "subfolder"
    dest_folder: str = ""        # used when dest_mode == "custom"
    subfolder_name: str = "Converted"
    on_existing: str = "skip"

    # --- runtime --------------------------------------------------------
    threads: int = 0             # 0 = auto (cpu_count)

    # --- ui -------------------------------------------------------------
    theme: str = "system"
    window_width: int = 940
    window_height: int = 720
    recent_folders: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    def worker_count(self) -> int:
        if self.threads > 0:
            return self.threads
        return max(1, min(16, (os.cpu_count() or 4)))

    def output_suffix(self) -> str:
        return {"jpeg": ".jpg"}.get(self.output_format, "." + self.output_format)

    def clamp(self) -> None:
        """Coerce every field back into a legal range. Called after load and
        before every run, so a hand-edited settings.json can't crash a batch."""
        self.output_format = _one_of(self.output_format, OUTPUT_FORMATS, "webp")
        # OUTPUT_FORMATS is what the app knows about; writable_formats() is what
        # this Pillow build can actually encode. A preset (or an old settings
        # file) could otherwise select a format that fails on every file — the
        # exact thing the capability probe exists to prevent.
        writable = writable_formats()
        if self.output_format not in writable:
            self.output_format = writable[0]
        self.resize_mode = _one_of(self.resize_mode, RESIZE_MODES, "none")
        self.square_mode = _one_of(self.square_mode, SQUARE_MODES, "off")
        self.dest_mode = _one_of(self.dest_mode, DEST_MODES, "subfolder")
        self.on_existing = _one_of(self.on_existing, ON_EXISTING, "skip")
        self.theme = _one_of(self.theme, THEMES, "system")

        self.quality = _clamp_int(self.quality, 1, 100, 85)  # match the field default
        self.effort = _clamp_int(self.effort, 0, 6, 6)
        self.threads = _clamp_int(self.threads, 0, 64, 0)
        self.window_width = _clamp_int(self.window_width, 720, 4000, 940)
        self.window_height = _clamp_int(self.window_height, 560, 3000, 720)

        lo, hi = (0.1, 500.0) if self.resize_mode == "megapixels" else (16.0, 30000.0)
        self.resize_value = _clamp_float(self.resize_value, lo, hi, 2560.0)

        if not (self.canvas_fill == "transparent" or _is_hex_color(self.canvas_fill)):
            self.canvas_fill = "transparent"
        if not isinstance(self.recent_folders, list):
            self.recent_folders = []
        self.recent_folders = [str(p) for p in self.recent_folders][:10]
        if not str(self.subfolder_name).strip():
            self.subfolder_name = "Converted"

    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        known = {f.name for f in fields(cls)}
        obj = cls(**{k: v for k, v in data.items() if k in known})
        obj.clamp()
        return obj

    def save(self) -> None:
        # Write-then-rename: a crash mid-write can't leave a truncated config.
        tmp = CONFIG_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(CONFIG_FILE)

    @classmethod
    def load(cls) -> "Settings":
        try:
            return cls.from_dict(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            return cls()

    def add_recent_folder(self, folder: Path) -> None:
        s = str(Path(folder).resolve())
        if s in self.recent_folders:
            self.recent_folders.remove(s)
        self.recent_folders.insert(0, s)
        self.recent_folders = self.recent_folders[:10]

    def apply_preset(self, name: str) -> None:
        for key, value in PRESETS.get(name, {}).items():
            setattr(self, key, value)
        self.clamp()

    def matching_preset(self) -> str:
        for name, values in PRESETS.items():
            if all(getattr(self, k) == v for k, v in values.items()):
                return name
        return "Custom"


# Presets only touch encode/geometry knobs — never destination or threads,
# so switching a preset can't silently redirect where files land.
PRESETS: dict[str, dict[str, Any]] = {
    "Web": {
        "output_format": "webp", "quality": 80, "lossless": False, "effort": 6,
        "resize_mode": "long_edge", "resize_value": 2048.0, "keep_metadata": False,
    },
    "Balanced": {
        "output_format": "webp", "quality": 85, "lossless": False, "effort": 6,
        "resize_mode": "none", "resize_value": 2560.0, "keep_metadata": True,
    },
    "Archive": {
        "output_format": "webp", "quality": 95, "lossless": False, "effort": 6,
        "resize_mode": "none", "resize_value": 2560.0, "keep_metadata": True,
    },
    "Smallest": {
        "output_format": "avif", "quality": 55, "lossless": False, "effort": 6,
        "resize_mode": "long_edge", "resize_value": 1600.0, "keep_metadata": False,
    },
}

PRESET_HINTS = {
    "Web": "2048 px · q80 WebP · metadata stripped",
    "Balanced": "Full size · q85 WebP · metadata kept",
    "Archive": "Full size · q95 WebP · metadata kept",
    "Smallest": "1600 px · q55 AVIF · metadata stripped",
    "Custom": "Your own settings",
}


# ---------------------------------------------------------------------------
_writable: tuple[str, ...] | None = None


def writable_formats() -> tuple[str, ...]:
    """Formats this Pillow build can encode. Imported lazily and cached —
    core.imaging imports this module, so a top-level import would cycle."""
    global _writable
    if _writable is None:
        try:
            from core.imaging import available_output_formats

            _writable = tuple(available_output_formats()) or OUTPUT_FORMATS
        except Exception:
            _writable = OUTPUT_FORMATS
    return _writable


def _one_of(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    return value if value in allowed else fallback


def _clamp_int(value: Any, lo: int, hi: int, fallback: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return fallback


def _clamp_float(value: Any, lo: float, hi: float, fallback: float) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return fallback


def _is_hex_color(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 7
        and value.startswith("#")
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )
