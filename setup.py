"""
py2app setup script for building macOS .app bundle.

Usage:
    python setup.py py2app

This will create a standalone .app in the dist/ folder.
"""

from setuptools import setup

APP = ['main.py']
APP_NAME = 'ConvertImagesToWebP'
VERSION = '0.1.0'

DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': 'ConvertImagesToWebP - MacAlpha',
        'CFBundleGetInfoString': 'High-performance image to WebP converter',
        'CFBundleIdentifier': 'com.webpconverter.macalpha',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'LSMinimumSystemVersion': '10.15',  # Catalina or later
        # File types this app can open
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Image File',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': [
                    'public.jpeg',
                    'public.png',
                    'public.tiff',
                    'public.heic',
                    'com.microsoft.bmp',
                ],
                'LSHandlerRank': 'Alternate',
            }
        ],
    },
    'packages': [
        'customtkinter',
        'PIL',
        'piexif',
        'gui',
        'core',
    ],
    'includes': [
        'tkinter',
        'gui.app',
        'gui.screens.dropzone',
        'gui.screens.settings',
        'gui.screens.progress',
        'gui.screens.results',
        'core.config',
        'core.converter',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
    ],
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
