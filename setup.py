"""py2app bundler for macOS.

    python setup.py py2app     ->  dist/WebP Studio.app
"""

from pathlib import Path

from setuptools import setup

APP_NAME = "WebP Studio"
VERSION = "2.0.0"
HERE = Path(__file__).parent
ICON = HERE / "assets" / "icon.icns"

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.webpstudio.app",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # allow dark mode
        # The real floor is whatever the building Python supports; python.org
        # universal2 builds go back to 10.13. v1 claimed 10.15 arbitrarily.
        "LSMinimumSystemVersion": "10.13",
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName": "Image",
            "CFBundleTypeRole": "Viewer",
            "LSItemContentTypes": ["public.jpeg", "public.png", "public.tiff",
                                   "public.heic", "org.webmproject.webp",
                                   "com.microsoft.bmp"],
            "LSHandlerRank": "Alternate",
        }],
    },
    # tkinterdnd2 ships a Tcl extension that py2app only copies when the whole
    # package is included, not just the importable module.
    "packages": ["customtkinter", "PIL", "tkinterdnd2", "gui", "core"],
    "includes": ["tkinter", "piexif"],
    # setuptools stays: py2app's own recipes import from it during the build,
    # and excluding it is a common cause of a bundle that dies on launch.
    "excludes": ["matplotlib", "numpy", "scipy", "pandas", "pytest"],
}

# v1 hardcoded an iconfile that was never committed, so every build failed.
if ICON.exists():
    OPTIONS["iconfile"] = str(ICON)

setup(
    app=["main.py"],
    name=APP_NAME,
    version=VERSION,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
