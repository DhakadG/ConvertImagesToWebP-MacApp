"""GUI boot + one real conversion, driven through the actual Tk event loop.

    python tests/test_gui_boot.py

Needs a display. The engine tests cover the conversion logic; this one exists
to catch the things that only break on a specific OS — a font family that
doesn't resolve, a widget option a platform's Tk rejects, a theme token that
blows up — and to prove the queue/poll plumbing between the worker threads and
the window actually completes a run.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before core.config is imported anywhere.
_CONFIG_DIR = tempfile.mkdtemp(prefix="webpstudio-test-")
os.environ["WEBP_STUDIO_CONFIG_DIR"] = _CONFIG_DIR

from PIL import Image

from gui.app import App


def build_sources(root: Path, count: int = 8) -> Path:
    folder = root / "shoot"
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        Image.new("RGB", (900, 600), (i * 25 % 255, 90, 200)).save(
            folder / f"pic_{i:02d}.jpg", quality=95)
    (folder / "broken.png").write_bytes(b"not an image")  # must not abort the run
    return folder


def pump(app: App, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


def wait_for(app: App, screen: str, timeout: float = 120.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        pump(app, 0.1)
        if app.current == screen:
            return
    raise AssertionError(f"stuck on {app.current!r}, expected {screen!r}")


def main() -> int:
    workspace = Path(tempfile.mkdtemp(prefix="webpstudio-work-"))
    source = build_sources(workspace)

    app = App()
    app.geometry("1060x760")
    pump(app, 0.5)

    # Every screen must construct on this platform, not just the first.
    for name in ("home", "progress", "results"):
        assert name in app.screens, name
    print("  all screens constructed")

    home = app.screens["home"]
    home.set_sources([source])
    pump(app, 3.0)
    assert home.scan is not None, "preflight scan never returned"
    assert len(home.scan.files) == 9, home.scan.files
    assert home.convert_button.cget("state") == "normal"
    print(f"  preflight ok — {home.summary.cget('text').splitlines()[0]}")

    home.start()
    wait_for(app, "results")

    results = app.screens["results"]
    produced = sorted((source / "Converted").glob("*.webp"))
    assert len(produced) == 8, [p.name for p in produced]
    with Image.open(produced[0]) as img:
        assert img.format == "WEBP" and img.size == (900, 600)
    assert results.headline.cget("text") == "Finished with errors"  # the broken file
    print(f"  converted {len(produced)} files · {results.headline.cget('text')}"
          f" · {results.subhead.cget('text')}")

    # Second pass must skip rather than redo, and must say so.
    app.go_home()
    pump(app, 3.0)
    home.start()
    wait_for(app, "results")
    assert "already existed" in results.subhead.cget("text"), results.subhead.cget("text")
    print(f"  rerun ok — {results.subhead.cget('text')}")

    # Theme switching repaints without raising (the ring is a raw Canvas).
    for theme in ("Light", "Dark", "System"):
        app._set_theme(theme)
        pump(app, 0.2)
    print("  theme switching ok")

    app.destroy()
    print("\ngui boot checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
