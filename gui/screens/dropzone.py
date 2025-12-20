"""
Screen 1: Drop Zone - Main landing screen for file/folder input.

Features:
- Large drag-and-drop area
- Browse buttons (files/folder)
- Recent folders quick access
- Settings shortcut
"""

import customtkinter as ctk
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from tkinter import filedialog
import platform

if TYPE_CHECKING:
    from gui.app import WebPConverterApp

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.config import config


class DropZoneScreen(ctk.CTkFrame):
    """
    Drop Zone screen - Main landing page for file selection.
    """

    def __init__(self, parent, app: "WebPConverterApp"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ─────────────────────────────────────────────────────────────────────
        # Header
        # ─────────────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        # App title
        title_label = ctk.CTkLabel(
            header_frame,
            text="WebP Converter",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Settings button (gear icon)
        settings_btn = ctk.CTkButton(
            header_frame,
            text="⚙️",
            width=40,
            height=40,
            corner_radius=20,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._open_settings
        )
        settings_btn.grid(row=0, column=1, sticky="e")

        # ─────────────────────────────────────────────────────────────────────
        # Drop Zone Area
        # ─────────────────────────────────────────────────────────────────────
        drop_frame = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray17"),
            corner_radius=20,
            border_width=3,
            border_color=("gray70", "gray40")
        )
        drop_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        drop_frame.grid_columnconfigure(0, weight=1)
        drop_frame.grid_rowconfigure(0, weight=1)

        # Inner content container
        inner_frame = ctk.CTkFrame(drop_frame, fg_color="transparent")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Drop icon (using emoji as placeholder - can replace with actual icon)
        drop_icon = ctk.CTkLabel(
            inner_frame,
            text="📁",
            font=ctk.CTkFont(size=64)
        )
        drop_icon.pack(pady=(0, 20))

        # Drop text
        drop_text = ctk.CTkLabel(
            inner_frame,
            text="Drop images or folders here",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        drop_text.pack(pady=(0, 5))

        # Subtitle
        subtitle = ctk.CTkLabel(
            inner_frame,
            text="or use the buttons below",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        subtitle.pack(pady=(0, 30))

        # Browse buttons container
        btn_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        btn_frame.pack()

        # Browse folder button
        browse_folder_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Browse Folder",
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            corner_radius=10,
            command=self._browse_folder
        )
        browse_folder_btn.grid(row=0, column=0, padx=10)

        # Browse files button
        browse_files_btn = ctk.CTkButton(
            btn_frame,
            text="🖼️ Browse Files",
            font=ctk.CTkFont(size=14),
            width=150,
            height=40,
            corner_radius=10,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._browse_files
        )
        browse_files_btn.grid(row=0, column=1, padx=10)

        # Make the drop zone clickable
        drop_frame.bind("<Button-1>", lambda e: self._browse_folder())

        # ─────────────────────────────────────────────────────────────────────
        # Recent Folders Section
        # ─────────────────────────────────────────────────────────────────────
        recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        recent_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 20))
        recent_frame.grid_columnconfigure(0, weight=1)

        if config.RECENT_FOLDERS:
            recent_label = ctk.CTkLabel(
                recent_frame,
                text="Recent Folders",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=("gray50", "gray60")
            )
            recent_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

            # Show up to 3 recent folders
            for i, folder_path in enumerate(config.RECENT_FOLDERS[:3]):
                folder = Path(folder_path)
                if folder.exists():
                    folder_btn = ctk.CTkButton(
                        recent_frame,
                        text=f"📁 {folder.name}",
                        font=ctk.CTkFont(size=12),
                        height=30,
                        corner_radius=8,
                        fg_color="transparent",
                        hover_color=("gray80", "gray30"),
                        text_color=("gray40", "gray70"),
                        anchor="w",
                        command=lambda p=folder: self._select_folder(p)
                    )
                    folder_btn.grid(row=i+1, column=0, sticky="ew", pady=2)

        # ─────────────────────────────────────────────────────────────────────
        # Footer
        # ─────────────────────────────────────────────────────────────────────
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 20))
        footer_frame.grid_columnconfigure(0, weight=1)

        version_label = ctk.CTkLabel(
            footer_frame,
            text=f"MacAlpha v{self.app.VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray50")
        )
        version_label.grid(row=0, column=0, sticky="w")

        # Supported formats hint
        formats_label = ctk.CTkLabel(
            footer_frame,
            text="JPG • PNG • BMP • TIFF • HEIC • WebP",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray50")
        )
        formats_label.grid(row=0, column=1, sticky="e")

    def _browse_folder(self):
        """Open folder browser dialog."""
        initial_dir = str(Path.home() / "Downloads")
        if config.RECENT_FOLDERS:
            recent = Path(config.RECENT_FOLDERS[0])
            if recent.exists():
                initial_dir = str(recent.parent)

        folder = filedialog.askdirectory(
            title="Select folder containing images",
            initialdir=initial_dir
        )

        if folder:
            self._select_folder(Path(folder))

    def _browse_files(self):
        """Open file browser dialog for multiple files."""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.heic"),
            ("All files", "*.*")
        ]

        files = filedialog.askopenfilenames(
            title="Select images to convert",
            filetypes=filetypes,
            initialdir=str(Path.home() / "Downloads")
        )

        if files:
            paths = [Path(f) for f in files]
            self.app.set_source_paths(paths)

            # Add parent folder to recent
            if paths:
                config.add_recent_folder(paths[0].parent)

            self.app.show_screen("settings")

    def _select_folder(self, folder: Path):
        """Handle folder selection."""
        self.app.set_source_paths([folder])
        config.add_recent_folder(folder)
        self.app.show_screen("settings")

    def _open_settings(self):
        """Open settings screen."""
        self.app.show_screen("settings")

    def on_show(self, **kwargs):
        """Called when this screen is shown."""
        pass  # Refresh recent folders if needed
