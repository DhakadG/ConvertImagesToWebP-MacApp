"""
Core Converter Module - WebP conversion engine.

This module wraps the v6 processing logic for use in the GUI app.
It provides a simplified interface for image conversion with progress callbacks.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import BytesIO
import threading

# Image processing imports
try:
    from PIL import Image, ImageOps, ImageCms
    import piexif
except ImportError:
    print("Required packages not installed. Run: pip install Pillow piexif")
    sys.exit(1)

# Import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import AppConfig

# Allow processing very large images
Image.MAX_IMAGE_PIXELS = None


@dataclass
class ConversionResult:
    """Result from converting a single image."""
    success: bool
    file_path: Path
    output_path: Optional[Path]
    error_message: Optional[str]
    original_size: int
    output_size: int
    was_skipped: bool = False
    was_copied: bool = False


def find_images(source_paths: List[Path], extensions: Tuple[str, ...]) -> List[Path]:
    """
    Find all image files from the given source paths.

    Args:
        source_paths: List of files and/or folders to search
        extensions: Tuple of valid file extensions (lowercase, with dot)

    Returns:
        List of image file paths
    """
    images = []
    extensions_lower = tuple(ext.lower() for ext in extensions)

    for source in source_paths:
        if source.is_file():
            if source.suffix.lower() in extensions_lower:
                images.append(source)
        elif source.is_dir():
            for ext in extensions:
                images.extend(source.rglob(f"*{ext}"))
                images.extend(source.rglob(f"*{ext.upper()}"))

    # Remove duplicates and sort
    images = sorted(set(images))
    return images


def get_safe_output_name(
    file_path: Path,
    output_folder: Path,
    root_folder: Path,
    extensions: Tuple[str, ...]
) -> Path:
    """
    Generate output path with smart collision detection.

    Only adds original extension suffix when there's an actual naming conflict.
    """
    try:
        rel_parent = file_path.relative_to(root_folder).parent
    except ValueError:
        rel_parent = Path()

    base_name = file_path.stem
    original_ext = file_path.suffix.lower()
    simple_name = f"{base_name}.webp"
    ext_suffix = original_ext[1:] if original_ext.startswith(".") else original_ext
    collision_name = f"{base_name}_{ext_suffix}.webp"

    output_dir = output_folder / rel_parent
    source_dir = file_path.parent

    try:
        conflicting_files = []
        for f in source_dir.iterdir():
            if not f.is_file():
                continue
            if f.stem.lower() != base_name.lower():
                continue
            if f.suffix.lower() == original_ext:
                continue
            if f.suffix.lower() in tuple(ext.lower() for ext in extensions):
                conflicting_files.append(f)

        if conflicting_files:
            return output_dir / collision_name
        else:
            return output_dir / simple_name
    except OSError:
        return output_dir / simple_name


def convert_to_srgb(img: Image.Image) -> Image.Image:
    """Convert image from wide-gamut to sRGB colorspace."""
    if img.mode not in ("RGB", "RGBA"):
        return img

    icc_profile = img.info.get("icc_profile")
    if not icc_profile:
        return img

    try:
        srgb_profile = ImageCms.createProfile("sRGB")
        source_profile = ImageCms.ImageCmsProfile(BytesIO(icc_profile))

        if img.mode == "RGBA":
            transform = ImageCms.buildTransformFromOpenProfiles(
                source_profile, srgb_profile, "RGBA", "RGBA"
            )
        else:
            transform = ImageCms.buildTransformFromOpenProfiles(
                source_profile, srgb_profile, "RGB", "RGB"
            )

        img = ImageCms.applyTransform(img, transform)
        img.info["icc_profile"] = ImageCms.ImageCmsProfile(srgb_profile).tobytes()
    except Exception:
        pass

    return img


def process_single_image(
    file_path: Path,
    output_folder: Path,
    config: AppConfig,
    root_folder: Optional[Path] = None
) -> ConversionResult:
    """
    Process a single image: resize, convert to WebP.

    Args:
        file_path: Path to source image
        output_folder: Destination folder for WebP output
        config: Configuration instance
        root_folder: Root folder for relative path calculation

    Returns:
        ConversionResult with success status and details
    """
    if root_folder is None:
        root_folder = file_path.parent

    original_size = 0
    output_size = 0

    try:
        # Get original size
        original_size = file_path.stat().st_size

        # Calculate output path
        destination = get_safe_output_name(file_path, output_folder, root_folder, config.EXTENSIONS)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Skip check - if destination exists and is newer
        if destination.exists():
            if destination.stat().st_mtime > file_path.stat().st_mtime:
                output_size = destination.stat().st_size
                return ConversionResult(
                    success=True,
                    file_path=file_path,
                    output_path=destination,
                    error_message=None,
                    original_size=original_size,
                    output_size=output_size,
                    was_skipped=True
                )

        # WebP direct copy
        if file_path.suffix.lower() == ".webp":
            shutil.copy2(file_path, destination)
            output_size = original_size
            return ConversionResult(
                success=True,
                file_path=file_path,
                output_path=destination,
                error_message=None,
                original_size=original_size,
                output_size=output_size,
                was_copied=True
            )

        # Open and process image
        with Image.open(file_path) as img:
            # Handle EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to sRGB
            img = convert_to_srgb(img)

            # Calculate current megapixels
            width, height = img.size
            current_mp = (width * height) / 1_000_000

            # Resize if needed
            if current_mp > config.TARGET_MEGAPIXELS:
                scale_factor = (config.TARGET_MEGAPIXELS / current_mp) ** 0.5
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Handle square modes
            if config.ENABLE_CROP_SQUARE:
                # Center crop to 1:1
                width, height = img.size
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                img = img.crop((left, top, left + size, top + size))

            elif config.ENABLE_SQUARE_CANVAS:
                # Fit into square canvas
                width, height = img.size
                size = max(width, height)

                if config.CANVAS_FILL_MODE == "transparent":
                    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                else:
                    canvas = Image.new("RGB", (size, size), config.CANVAS_FILL_COLOR)

                x = (size - width) // 2
                y = (size - height) // 2
                canvas.paste(img, (x, y))
                img = canvas

            # Prepare for WebP save
            save_kwargs = {
                "quality": config.QUALITY,
                "method": config.WEBP_METHOD,
            }

            # Handle transparency
            if img.mode == "RGBA":
                save_kwargs["lossless"] = False
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Save as WebP
            img.save(destination, "WebP", **save_kwargs)

            output_size = destination.stat().st_size

        return ConversionResult(
            success=True,
            file_path=file_path,
            output_path=destination,
            error_message=None,
            original_size=original_size,
            output_size=output_size
        )

    except Exception as e:
        return ConversionResult(
            success=False,
            file_path=file_path,
            output_path=None,
            error_message=str(e),
            original_size=original_size,
            output_size=0
        )


def run_batch_conversion(
    images: List[Path],
    output_folder: Path,
    root_folder: Path,
    config: AppConfig,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_threads: int = 8
) -> List[ConversionResult]:
    """
    Convert a batch of images with parallel processing.

    Args:
        images: List of image paths to convert
        output_folder: Destination folder
        root_folder: Root folder for relative paths
        config: Configuration instance
        progress_callback: Optional callback(completed, total, current_file)
        max_threads: Maximum parallel threads

    Returns:
        List of ConversionResult objects
    """
    results = []
    total = len(images)
    completed = 0
    results_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_path = {
            executor.submit(process_single_image, img, output_folder, config, root_folder): img
            for img in images
        }

        for future in as_completed(future_to_path):
            img_path = future_to_path[future]

            try:
                result = future.result()
            except Exception as e:
                result = ConversionResult(
                    success=False,
                    file_path=img_path,
                    output_path=None,
                    error_message=str(e),
                    original_size=0,
                    output_size=0
                )

            with results_lock:
                results.append(result)
                completed += 1

            if progress_callback:
                progress_callback(completed, total, img_path.name)

    return results
