#!/usr/bin/env python3
"""WebP Studio — entry point.

    python main.py            launch the app
    python main.py --check    report which optional features are available
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REQUIRED = {"customtkinter": "customtkinter", "PIL": "Pillow"}
OPTIONAL = {
    "tkinterdnd2": ("tkinterdnd2", "drag & drop"),
    "piexif": ("piexif", "removing GPS tags while keeping other metadata"),
    "pillow_heif": ("pillow-heif", "reading iPhone HEIC files"),
}


def tk_problem() -> str | None:
    """macOS ships Tk 8.5.9, which renders CustomTkinter as black boxes and
    ignores dark mode. Naming it beats letting the user file a bug about it."""
    try:
        import tkinter
    except ImportError:
        return ("tkinter is not available. On macOS: brew install python-tk\n"
                "On Debian/Ubuntu: sudo apt install python3-tk")
    if tkinter.TkVersion < 8.6:
        return (f"Tk {tkinter.TkVersion} is too old (8.6+ required) — widgets will "
                f"render incorrectly.\nOn macOS: brew install python python-tk, then "
                f"run this with the Homebrew python3.")
    return None


def _missing_required() -> list[str]:
    missing = []
    for module, package in REQUIRED.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def check() -> int:
    import platform as _platform

    print(f"python   {sys.version.split()[0]} on {_platform.system()} "
          f"{_platform.machine()}")
    problem = tk_problem()
    print(f"tk       {'PROBLEM — ' + problem.splitlines()[0] if problem else 'ok'}")

    missing = _missing_required()
    for package in missing:
        print(f"missing (required): {package}")

    for module, (package, why) in OPTIONAL.items():
        try:
            __import__(module)
            print(f"ok       {package}")
        except ImportError:
            print(f"absent   {package}  — no {why}")

    try:
        from core.imaging import available_output_formats

        print("writable formats:", ", ".join(available_output_formats()))
    except ImportError:
        pass
    return 1 if missing else 0


def main() -> int:
    if "--check" in sys.argv:
        return check()

    problem = tk_problem()
    if problem:
        print(problem)
        return 1

    missing = _missing_required()
    if missing:
        print("Missing required packages:", ", ".join(missing))
        print("\n  pip install -r requirements.txt\n")
        return 1

    from gui.app import main as run

    return run()


if __name__ == "__main__":
    sys.exit(main())
