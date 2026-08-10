"""Engine self-check. No framework: `python tests/test_engine.py`.

Covers the logic that silently corrupts a batch when wrong — sizing math,
destination collisions, the skip/overwrite/rename policies, metadata, cancel.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from core.config import Settings
from core.imaging import _target_size, available_output_formats, convert_file
from core.runner import CONVERTED, FAILED, SKIPPED, Runner, scan_sources, common_root


def make_image(path: Path, size=(800, 600), color="red", mode="RGB") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size, color).save(path)
    return path


def test_target_size():
    s = Settings()
    s.resize_mode = "none"
    assert _target_size(4000, 3000, s) == (4000, 3000)

    s.resize_mode, s.resize_value = "long_edge", 1000
    assert _target_size(4000, 2000, s) == (1000, 500)
    assert _target_size(2000, 4000, s) == (500, 1000)
    # never upscales
    assert _target_size(400, 200, s) == (400, 200)

    s.resize_mode, s.resize_value = "width", 300
    assert _target_size(900, 600, s) == (300, 200)

    s.resize_mode, s.resize_value = "height", 300
    assert _target_size(900, 600, s) == (450, 300)

    s.resize_mode, s.resize_value = "megapixels", 1.0
    w, h = _target_size(4000, 3000, s)
    assert 0.98 <= (w * h) / 1_000_000 <= 1.02, (w, h)
    print("  target_size ok")


def test_settings_clamp():
    s = Settings.from_dict({"quality": 900, "output_format": "gif", "effort": -4,
                            "on_existing": "nuke", "canvas_fill": "banana"})
    assert s.quality == 100 and s.output_format == "webp"
    assert s.effort == 0 and s.on_existing == "skip"
    assert s.canvas_fill == "transparent"
    assert Settings(output_format="jpeg").output_suffix() == ".jpg"
    print("  settings clamp ok")


def test_convert_and_resize(tmp: Path):
    src = make_image(tmp / "in" / "photo.png", (1600, 900))
    s = Settings(output_format="webp", resize_mode="long_edge", resize_value=800)
    out = tmp / "out" / "photo.webp"
    convert_file(src, out, s)
    with Image.open(out) as img:
        assert img.size == (800, 450), img.size
        assert img.format == "WEBP"
    print("  convert + resize ok")


def test_alpha_to_jpeg(tmp: Path):
    """RGBA into a format with no alpha must flatten, not raise."""
    src = make_image(tmp / "in" / "alpha.png", (100, 100), (255, 0, 0, 128), "RGBA")
    out = tmp / "out" / "alpha.jpg"
    convert_file(src, out, Settings(output_format="jpeg"))
    with Image.open(out) as img:
        assert img.mode == "RGB"
    print("  alpha flatten ok")


def test_square_modes(tmp: Path):
    src = make_image(tmp / "in" / "wide.png", (400, 200))
    for mode, expected in (("crop", (200, 200)), ("canvas", (400, 400))):
        out = tmp / "out" / f"{mode}.webp"
        convert_file(src, out, Settings(square_mode=mode))
        with Image.open(out) as img:
            assert img.size == expected, (mode, img.size)
    print("  square modes ok")


def test_metadata(tmp: Path):
    src = tmp / "in" / "meta.jpg"
    src.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (60, 60), "blue")
    exif = img.getexif()
    exif[0x010F] = "SelfCheckCamera"  # Make
    img.save(src, exif=exif)

    kept = tmp / "out" / "kept.webp"
    convert_file(src, kept, Settings(keep_metadata=True))
    with Image.open(kept) as out:
        assert out.getexif().get(0x010F) == "SelfCheckCamera", "EXIF was dropped"

    stripped = tmp / "out" / "stripped.webp"
    convert_file(src, stripped, Settings(keep_metadata=False))
    with Image.open(stripped) as out:
        assert not out.getexif().get(0x010F), "EXIF survived a strip"
    print("  metadata keep/strip ok")


def test_scan_excludes_output(tmp: Path):
    root = tmp / "shoot"
    make_image(root / "a.png")
    make_image(root / "nested" / "b.png")
    make_image(root / "Converted" / "a.webp")

    scan = scan_sources([root], (".png", ".webp"), exclude_under=root / "Converted")
    names = {p.name for p in scan.files}
    assert names == {"a.png", "b.png"}, names
    assert scan.total_bytes > 0
    assert common_root([root / "a.png", root / "nested" / "b.png"]) == root.resolve()
    print("  scan excludes output ok")


def test_on_existing_policies(tmp: Path):
    root = tmp / "batch"
    make_image(root / "one.png")

    def run(policy: str) -> list:
        s = Settings(on_existing=policy, dest_mode="subfolder", subfolder_name="Out")
        scan = scan_sources([root], (".png",), exclude_under=root / "Out")
        return Runner(scan, s).run()

    first = run("skip")
    assert first[0].status == CONVERTED and first[0].destination.exists()
    first_size = first[0].destination.stat().st_size

    assert run("skip")[0].status == SKIPPED
    assert run("overwrite")[0].status == CONVERTED
    assert (root / "Out" / "one.webp").stat().st_size == first_size

    renamed = run("rename")
    assert renamed[0].status == CONVERTED
    assert renamed[0].destination.name == "one_1.webp", renamed[0].destination
    print("  skip/overwrite/rename ok")


def test_collision_within_one_run(tmp: Path):
    """one.png and one.jpg both want one.webp — neither may be lost."""
    root = tmp / "collide"
    make_image(root / "one.png")
    make_image(root / "one.jpg")
    scan = scan_sources([root], (".png", ".jpg"), exclude_under=root / "Out")
    results = Runner(scan, Settings(subfolder_name="Out", on_existing="skip")).run()

    assert all(r.status == CONVERTED for r in results), [r.status for r in results]
    outputs = {r.destination.name for r in results}
    assert len(outputs) == 2, outputs
    print("  in-run collision ok")


def test_failure_is_isolated(tmp: Path):
    root = tmp / "mixed"
    make_image(root / "good.png")
    (root / "broken.png").write_bytes(b"this is not a png")

    scan = scan_sources([root], (".png",), exclude_under=root / "Out")
    results = Runner(scan, Settings(subfolder_name="Out")).run()
    by_status = {r.source.name: r.status for r in results}

    assert by_status["good.png"] == CONVERTED
    assert by_status["broken.png"] == FAILED
    assert not (root / "Out" / "broken.webp").exists(), "left a truncated file behind"
    print("  bad file isolated ok")


def test_cancel(tmp: Path):
    root = tmp / "many"
    for i in range(24):
        make_image(root / f"img_{i:02d}.png", (200, 200))

    scan = scan_sources([root], (".png",), exclude_under=root / "Out")
    runner = Runner(scan, Settings(subfolder_name="Out", threads=1))
    runner.cancel()  # cancel before it starts: every file must report, none convert
    results = runner.run()

    assert len(results) == 24
    assert runner.cancelled
    assert sum(1 for r in results if r.status == CONVERTED) == 0
    print("  cancel ok")


def test_savings_accounting(tmp: Path):
    root = tmp / "stats"
    make_image(root / "big.png", (1200, 1200), "green")
    scan = scan_sources([root], (".png",), exclude_under=root / "Out")
    results = Runner(scan, Settings(subfolder_name="Out", quality=60)).run()
    r = results[0]
    assert r.source_bytes > 0 and r.output_bytes > 0
    assert r.saved_bytes == r.source_bytes - r.output_bytes
    print(f"  savings accounting ok ({r.source_bytes} -> {r.output_bytes} bytes)")


def main() -> int:
    print(f"writable formats: {', '.join(available_output_formats())}\n")
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        test_target_size()
        test_settings_clamp()
        test_convert_and_resize(tmp / "t1")
        test_alpha_to_jpeg(tmp / "t2")
        test_square_modes(tmp / "t3")
        test_metadata(tmp / "t4")
        test_scan_excludes_output(tmp / "t5")
        test_on_existing_policies(tmp / "t6")
        test_collision_within_one_run(tmp / "t7")
        test_failure_is_isolated(tmp / "t8")
        test_cancel(tmp / "t9")
        test_savings_accounting(tmp / "t10")
    print("\nall engine checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
