"""
Screen 2: Settings - Configuration options before processing.

Features:
- Quality slider (1-100)
- Resolution limit dropdown
- WebP method (encoding speed)
- Metadata toggle
- Square mode options (Original/Crop/Canvas)
- Start Processing button
"""

import customtkinter as ctk
from pathlib import Path
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from gui.app import WebPConverterApp

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.config import config


class SettingsScreen(ctk.CTkFrame):
    """
    Settings screen - Configure conversion options before processing.
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
        # Header with back button
        # ─────────────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        # Back button
        back_btn = ctk.CTkButton(
            header_frame,
            text="← Back",
            width=80,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            command=self._go_back
        )
        back_btn.grid(row=0, column=0, sticky="w")

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=1, sticky="w", padx=(20, 0))

        # ─────────────────────────────────────────────────────────────────────
        # Scrollable content area
        # ─────────────────────────────────────────────────────────────────────
        content_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)

        row = 0

        # ─────────────────────────────────────────────────────────────────────
        # Quality Section
        # ─────────────────────────────────────────────────────────────────────
        quality_section = self._create_section(content_frame, "📊 Quality", row)
        row += 1

        quality_frame = ctk.CTkFrame(content_frame, fg_color=("gray90", "gray17"), corner_radius=12)
        quality_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        quality_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Quality slider
        self.quality_var = ctk.IntVar(value=config.QUALITY)
        self.quality_label = ctk.CTkLabel(
            quality_frame,
            text=f"{config.QUALITY}%",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.quality_label.grid(row=0, column=0, sticky="e", padx=20, pady=(15, 5))

        quality_slider = ctk.CTkSlider(
            quality_frame,
            from_=1,
            to=100,
            variable=self.quality_var,
            command=self._on_quality_change
        )
        quality_slider.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 5))

        quality_hint = ctk.CTkLabel(
            quality_frame,
            text="Lower = smaller file, Higher = better quality",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        quality_hint.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 15))

        # ─────────────────────────────────────────────────────────────────────
        # Resolution Section
        # ─────────────────────────────────────────────────────────────────────
        res_section = self._create_section(content_frame, "📐 Resolution Limit", row)
        row += 1

        res_frame = ctk.CTkFrame(content_frame, fg_color=("gray90", "gray17"), corner_radius=12)
        res_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        res_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Resolution presets
        self.resolution_options = {
            "Original (No limit)": 500.0,
            "4K (8 MP)": 8.0,
            "5K (14.7 MP)": 14.7,
            "6K (19 MP)": 19.0,
            "8K (33 MP)": 33.0,
            "Custom": config.TARGET_MEGAPIXELS
        }

        # Find current selection
        current_res = "Custom"
        for name, val in self.resolution_options.items():
            if val == config.TARGET_MEGAPIXELS:
                current_res = name
                break

        self.res_dropdown = ctk.CTkOptionMenu(
            res_frame,
            values=list(self.resolution_options.keys()),
            command=self._on_resolution_change
        )
        self.res_dropdown.set(current_res)
        self.res_dropdown.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        # ─────────────────────────────────────────────────────────────────────
        # WebP Method Section
        # ─────────────────────────────────────────────────────────────────────
        method_section = self._create_section(content_frame, "⚡ Encoding Speed", row)
        row += 1

        method_frame = ctk.CTkFrame(content_frame, fg_color=("gray90", "gray17"), corner_radius=12)
        method_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        method_frame.grid_columnconfigure(0, weight=1)
        row += 1

        self.method_var = ctk.IntVar(value=config.WEBP_METHOD)

        method_options = ctk.CTkSegmentedButton(
            method_frame,
            values=["1 Fast", "2", "3", "4", "5", "6 Best"],
            command=self._on_method_change
        )
        method_options.set(f"{config.WEBP_METHOD}" if config.WEBP_METHOD not in [1, 6]
                          else ("1 Fast" if config.WEBP_METHOD == 1 else "6 Best"))
        method_options.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        # ─────────────────────────────────────────────────────────────────────
        # Metadata Toggle
        # ─────────────────────────────────────────────────────────────────────
        meta_section = self._create_section(content_frame, "💾 Metadata", row)
        row += 1

        meta_frame = ctk.CTkFrame(content_frame, fg_color=("gray90", "gray17"), corner_radius=12)
        meta_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        meta_frame.grid_columnconfigure(0, weight=1)
        row += 1

        self.metadata_var = ctk.BooleanVar(value=config.KEEP_METADATA)

        meta_switch = ctk.CTkSwitch(
            meta_frame,
            text="Preserve EXIF & color profiles",
            variable=self.metadata_var,
            command=self._on_metadata_change
        )
        meta_switch.grid(row=0, column=0, sticky="w", padx=20, pady=15)

        # ─────────────────────────────────────────────────────────────────────
        # Square Mode Section
        # ─────────────────────────────────────────────────────────────────────
        square_section = self._create_section(content_frame, "🔲 Square Mode", row)
        row += 1

        square_frame = ctk.CTkFrame(content_frame, fg_color=("gray90", "gray17"), corner_radius=12)
        square_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        square_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Determine current mode
        if config.ENABLE_CROP_SQUARE:
            current_square = "Crop"
        elif config.ENABLE_SQUARE_CANVAS:
            current_square = "Canvas"
        else:
            current_square = "Original"

        self.square_options = ctk.CTkSegmentedButton(
            square_frame,
            values=["Original", "Crop", "Canvas"],
            command=self._on_square_change
        )
        self.square_options.set(current_square)
        self.square_options.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        # ─────────────────────────────────────────────────────────────────────
        # Footer with Start Button
        # ─────────────────────────────────────────────────────────────────────
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(10, 30))
        footer_frame.grid_columnconfigure(0, weight=1)

        # Source info
        self.source_label = ctk.CTkLabel(
            footer_frame,
            text="No source selected",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        self.source_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Start button
        start_btn = ctk.CTkButton(
            footer_frame,
            text="▶️  Start Processing",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=12,
            command=self._start_processing
        )
        start_btn.grid(row=1, column=0, sticky="ew")

    def _create_section(self, parent, title: str, row: int) -> ctk.CTkLabel:
        """Create a section header label."""
        label = ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray40", "gray70")
        )
        label.grid(row=row, column=0, sticky="w", pady=(10, 5))
        return label

    def _on_quality_change(self, value):
        """Handle quality slider change."""
        val = int(value)
        self.quality_label.configure(text=f"{val}%")
        config.QUALITY = val

    def _on_resolution_change(self, choice):
        """Handle resolution dropdown change."""
        config.TARGET_MEGAPIXELS = self.resolution_options.get(choice, 19.0)

    def _on_method_change(self, choice):
        """Handle encoding method change."""
        method_map = {"1 Fast": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6 Best": 6}
        config.WEBP_METHOD = method_map.get(choice, 6)

    def _on_metadata_change(self):
        """Handle metadata toggle change."""
        config.KEEP_METADATA = self.metadata_var.get()

    def _on_square_change(self, choice):
        """Handle square mode change."""
        config.ENABLE_CROP_SQUARE = (choice == "Crop")
        config.ENABLE_SQUARE_CANVAS = (choice == "Canvas")

    def _go_back(self):
        """Navigate back to drop zone."""
        config.save()
        self.app.show_screen("dropzone")

    def _start_processing(self):
        """Start the conversion process."""
        config.save()

        if not self.app.source_paths:
            return  # No source selected

        self.app.start_processing()

    def on_show(self, **kwargs):
        """Called when this screen is shown."""
        # Update source label
        if self.app.source_paths:
            count = len(self.app.source_paths)
            if count == 1 and self.app.source_paths[0].is_dir():
                self.source_label.configure(text=f"📁 {self.app.source_paths[0].name}")
            else:
                self.source_label.configure(text=f"🖼️ {count} item{'s' if count > 1 else ''} selected")
        else:
            self.source_label.configure(text="No source selected")
