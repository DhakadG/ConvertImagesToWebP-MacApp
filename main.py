#!/usr/bin/env python3
"""
ConvertImagesToWebP - MacAlpha v0.1

Main entry point for the macOS GUI application.
"""

import sys
from pathlib import Path

# Ensure the app directory is in the path
APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

# Check dependencies before importing
def check_dependencies():
    """Check and report missing dependencies."""
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    try:
        import piexif
    except ImportError:
        missing.append("piexif")

    if missing:
        print("❌ Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nInstall with:")
        print(f"   pip install {' '.join(missing)}")
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()

    from gui.app import main
    main()
