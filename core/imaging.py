"""Single-image pipeline: open → orient → resize → square → encode.

Everything here is pure and thread-safe: no shared state, no UI, no disk
scanning. `convert_file` is the only entry point the runner needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, features

from core.config import Settings

# Raised, not disabled: legitimate scans and panoramas run well past Pillow's
# ~89 MP default, but a folder can still contain a downloaded or crafted file
# with an absurd declared size. Pillow itself only *warns* (doesn't raise)
# between 1x and 2x this value, so the real gate is the explicit check in
# convert_file below; this just keeps Pillow's own internal calls bounded too.
MAX_PIXELS = 300_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

# Optional decoders. Both are pure-import side effects, so probe once at module
# load rather than per-file.
try:  # HEIC/HEIF from iPhones
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:
    HEIF_OK = False

try:
    import piexif  # type: ignore

    PIEXIF_OK = True
except Exception:
    PIEXIF_OK = False


def available_output_formats() -> list[str]:
    """Formats this Pillow build can actually write. Offering a format the
    install can't encode is how you get a 500-file batch that fails on file 1."""
    out = ["jpeg", "png"]
    if features.check("webp"):
        out.insert(0, "webp")
    try:
        if features.check("avif"):
            out.insert(1 if "webp" in out else 0, "avif")
    except Exception:
        pass
    return out


def readable_extensions(all_extensions: tuple[str, ...]) -> tuple[str, ...]:
    """Drop HEIC/HEIF from the scan filter when no HEIF decoder is installed."""
    if HEIF_OK:
        return all_extensions
    return tuple(e for e in all_extensions if e not in (".heic", ".heif"))


@dataclass
class Encoded:
    width: int
    height: int
    note: str = ""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def _prepare_exif(raw: bytes | None, strip_gps: bool) -> bytes | None:
    if not raw:
        return None
    if not strip_gps:
        return raw
    if not PIEXIF_OK:
        # Can't surgically remove GPS, so drop the whole block rather than
        # silently shipping the coordinates the user asked to remove.
        return None
    try:
        data = piexif.load(raw)
        data["GPS"] = {}
        return piexif.dump(data)
    except Exception:
        return None


def _to_srgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    """Bake a wide-gamut profile into sRGB pixels.

    Only used when metadata is being dropped: an untagged file is interpreted
    as sRGB by every viewer, so without this the colors shift visibly.
    """
    if not icc or img.mode not in ("RGB", "RGBA"):
        return img
    try:
        src = ImageCms.ImageCmsProfile(BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(img, src, dst, outputMode=img.mode) or img
    except Exception:
        return img  # bad/exotic profile: better untouched than crashed


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def _target_size(width: int, height: int, settings: Settings) -> tuple[int, int]:
    """Return the new size, downscale-only. Upscaling never adds detail, it
    just makes the file bigger, so a limit above the source is a no-op."""
    mode, value = settings.resize_mode, settings.resize_value
    if mode == "none" or width <= 0 or height <= 0:
        return width, height

    if mode == "megapixels":
        current_mp = (width * height) / 1_000_000
        if current_mp <= value:
            return width, height
        scale = (value / current_mp) ** 0.5
    elif mode == "long_edge":
        longest = max(width, height)
        if longest <= value:
            return width, height
        scale = value / longest
    elif mode == "width":
        if width <= value:
            return width, height
        scale = value / width
    elif mode == "height":
        if height <= value:
            return width, height
        scale = value / height
    else:
        return width, height

    return max(1, round(width * scale)), max(1, round(height * scale))


def _apply_square(img: Image.Image, settings: Settings) -> Image.Image:
    if settings.square_mode == "crop":
        w, h = img.size
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        return img.crop((left, top, left + side, top + side))

    if settings.square_mode == "canvas":
        w, h = img.size
        side = max(w, h)
        if settings.canvas_fill == "transparent":
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
        else:
            canvas = Image.new("RGB", (side, side), settings.canvas_fill)
            img = _flatten(img, settings.canvas_fill)
        canvas.paste(img, ((side - w) // 2, (side - h) // 2))
        return canvas

    return img


def _flatten(img: Image.Image, background: str) -> Image.Image:
    """Composite alpha onto a solid color — required for JPEG, which has none."""
    if img.mode not in ("RGBA", "LA", "PA") and "transparency" not in img.info:
        return img.convert("RGB")
    img = img.convert("RGBA")
    color = background if background != "transparent" else "#ffffff"
    base = Image.new("RGBA", img.size, color)
    return Image.alpha_composite(base, img).convert("RGB")


def _normalize_mode(img: Image.Image, output_format: str, settings: Settings) -> Image.Image:
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    if output_format == "jpeg":
        return _flatten(img, settings.canvas_fill) if has_alpha else img.convert("RGB")
    if has_alpha:
        return img if img.mode == "RGBA" else img.convert("RGBA")
    return img if img.mode == "RGB" else img.convert("RGB")


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------
def _save_kwargs(settings: Settings, exif: bytes | None, icc: bytes | None) -> dict:
    fmt = settings.output_format
    kwargs: dict = {}

    if fmt == "webp":
        kwargs.update(quality=settings.quality, method=settings.effort)
        if settings.lossless:
            # `exact` keeps RGB values under fully-transparent pixels, which
            # lossless mode is otherwise free to discard.
            kwargs.update(lossless=True, exact=True)
    elif fmt == "avif":
        # Pillow's AVIF `speed` is inverted vs WebP's `method`: 0 is slowest.
        # No lossless here: quality=100 is near-lossless, not lossless, and
        # calling it "lossless" in the UI would be a lie. The panel only offers
        # the toggle for WebP (PNG is lossless by definition).
        kwargs.update(quality=settings.quality, speed=max(0, 6 - settings.effort))
    elif fmt == "jpeg":
        kwargs.update(quality=settings.quality, optimize=True, progressive=True,
                      subsampling="4:4:4" if settings.quality >= 90 else "4:2:0")
    elif fmt == "png":
        kwargs.update(optimize=True, compress_level=min(9, settings.effort + 3))

    if exif:
        kwargs["exif"] = exif
    if icc:
        kwargs["icc_profile"] = icc
    return kwargs


PIL_FORMAT = {"webp": "WEBP", "avif": "AVIF", "jpeg": "JPEG", "png": "PNG"}

# Hard format ceilings. WebP's is a container limit, not a Pillow one, so a
# large panorama or flatbed scan fails at encode time with a message that says
# nothing useful. Check first and explain what to do about it.
MAX_DIMENSION = {"webp": 16383, "jpeg": 65535}


def _check_dimensions(width: int, height: int, output_format: str) -> None:
    limit = MAX_DIMENSION.get(output_format)
    if limit and (width > limit or height > limit):
        raise ValueError(
            f"{width}x{height} exceeds the {output_format.upper()} limit of "
            f"{limit}px — set a downscale limit, or choose PNG/AVIF")


def _check_pixel_count(width: int, height: int) -> None:
    """Pillow only warns, and still decodes, between 1x and 2x MAX_PIXELS —
    this is the actual gate. Called right after Image.open(), before any
    pixel data is touched, so an oversized file costs a header read, not a
    full decode."""
    pixels = width * height
    if pixels > MAX_PIXELS:
        raise ValueError(
            f"{width}x{height} ({pixels:,} px) exceeds the {MAX_PIXELS:,} px "
            f"safety limit — skipped before decoding")


def convert_file(source: Path, destination: Path, settings: Settings) -> Encoded:
    """Convert one image. Raises on failure — the runner turns that into a
    per-file error row so one bad file can't abort the batch."""
    note = ""
    with Image.open(source) as opened:
        _check_pixel_count(*opened.size)

        if getattr(opened, "n_frames", 1) > 1:
            note = "animated source, first frame only"

        img = ImageOps.exif_transpose(opened) or opened  # honor camera rotation
        icc = img.info.get("icc_profile")
        exif = _prepare_exif(img.info.get("exif"), settings.strip_gps) if settings.keep_metadata else None

        if not settings.keep_metadata:
            img = _to_srgb(img, icc)
            icc = None

        new_size = _target_size(*img.size, settings)
        if new_size != img.size:
            img = img.resize(new_size, Image.LANCZOS)

        img = _apply_square(img, settings)
        img = _normalize_mode(img, settings.output_format, settings)
        _check_dimensions(img.width, img.height, settings.output_format)

        destination.parent.mkdir(parents=True, exist_ok=True)
        img.save(destination, PIL_FORMAT[settings.output_format],
                 **_save_kwargs(settings, exif, icc))
        return Encoded(img.width, img.height, note)
