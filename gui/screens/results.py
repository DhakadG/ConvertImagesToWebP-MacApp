"""
Screen 4: Results - Processing summary and completion display.

Features:
- Success/failure summary
- File size savings stats
- Processing time
- Open output folder button
- Convert more / Done buttons
"""

import customtkinter as ctk
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any
import subprocess
import platform

if TYPE_CHECKING:
    from gui.app import WebPConverterApp

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.config import config


class ResultsScreen(ctk.CTkFrame):
    """
    Results screen - Shows processing summary after completion.
    """

    def __init__(self, parent, app: "WebPConverterApp"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.results: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ─────────────────────────────────────────────────────────────────────
        # Header with Success Icon
        # ─────────────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(40, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        # Success icon
        self.status_icon = ctk.CTkLabel(
            header_frame,
            text="✅",
            font=ctk.CTkFont(size=64)
        )
        self.status_icon.grid(row=0, column=0, pady=(0, 10))

        # Title
        self.title_label = ctk.CTkLabel(
            header_frame,
            text="Conversion Complete!",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=1, column=0)

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text="All images converted successfully",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray60")
        )
        self.subtitle_label.grid(row=2, column=0, pady=(5, 0))

        # ─────────────────────────────────────────────────────────────────────
        # Stats Cards
        # ─────────────────────────────────────────────────────────────────────
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=30)
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        # Files stat card
        files_card = ctk.CTkFrame(
            stats_frame,
            fg_color=("gray90", "gray17"),
            corner_radius=16
        )
        files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        self.files_count = ctk.CTkLabel(
            files_card,
            text="0",
            font=ctk.CTkFont(size=36, weight="bold")
        )
        self.files_count.pack(pady=(20, 5))

        files_label = ctk.CTkLabel(
            files_card,
            text="Images Converted",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        files_label.pack(pady=(0, 20))

        # Savings stat card
        savings_card = ctk.CTkFrame(
            stats_frame,
            fg_color=("gray90", "gray17"),
            corner_radius=16
        )
        savings_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        self.savings_percent = ctk.CTkLabel(
            savings_card,
            text="0%",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=("green", "#4ade80")
        )
        self.savings_percent.pack(pady=(20, 5))

        savings_label = ctk.CTkLabel(
            savings_card,
            text="Space Saved",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        savings_label.pack(pady=(0, 20))

        # ─────────────────────────────────────────────────────────────────────
        # Details Section
        # ─────────────────────────────────────────────────────────────────────
        details_frame = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray17"),
            corner_radius=16
        )
        details_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        details_frame.grid_columnconfigure(1, weight=1)

        # Before size
        before_label = ctk.CTkLabel(
            details_frame,
            text="Before:",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        before_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

        self.before_size = ctk.CTkLabel(
            details_frame,
            text="--",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.before_size.grid(row=0, column=1, sticky="e", padx=20, pady=(20, 5))

        # After size
        after_label = ctk.CTkLabel(
            details_frame,
            text="After:",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        after_label.grid(row=1, column=0, sticky="w", padx=20, pady=5)

        self.after_size = ctk.CTkLabel(
            details_frame,
            text="--",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("green", "#4ade80")
        )
        self.after_size.grid(row=1, column=1, sticky="e", padx=20, pady=5)

        # Processing time
        time_label = ctk.CTkLabel(
            details_frame,
            text="Time:",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        time_label.grid(row=2, column=0, sticky="w", padx=20, pady=(5, 20))

        self.time_value = ctk.CTkLabel(
            details_frame,
            text="--",
            font=ctk.CTkFont(size=13)
        )
        self.time_value.grid(row=2, column=1, sticky="e", padx=20, pady=(5, 20))

        # Output folder
        folder_label = ctk.CTkLabel(
            details_frame,
            text="Output:",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        folder_label.grid(row=3, column=0, sticky="w", padx=20, pady=(5, 20))

        self.folder_path = ctk.CTkLabel(
            details_frame,
            text="--",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        self.folder_path.grid(row=3, column=1, sticky="e", padx=20, pady=(5, 20))

        # ─────────────────────────────────────────────────────────────────────
        # Footer Buttons
        # ─────────────────────────────────────────────────────────────────────
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(10, 30))
        footer_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Open folder button
        open_btn = ctk.CTkButton(
            footer_frame,
            text="📂 Open Folder",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._open_output_folder
        )
        open_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # Convert more button
        more_btn = ctk.CTkButton(
            footer_frame,
            text="🔄 Convert More",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            command=self._convert_more
        )
        more_btn.grid(row=0, column=1, sticky="ew", padx=10)

        # Done button
        done_btn = ctk.CTkButton(
            footer_frame,
            text="✓ Done",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            fg_color=("green", "#22c55e"),
            hover_color=("darkgreen", "#16a34a"),
            command=self._done
        )
        done_btn.grid(row=0, column=2, sticky="ew", padx=(10, 0))

    def _format_bytes(self, size_bytes: int) -> str:
        """Format byte size as human-readable string."""
        if size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def _update_stats(self, results: List[Dict[str, Any]]):
        """Update the stats display with processing results."""
        total = len(results)
        successful = sum(1 for r in results if r.get("success", False))

        # Calculate sizes
        total_before = sum(r.get("original_size", 0) for r in results)
        total_after = sum(r.get("output_size", 0) for r in results)
        saved = total_before - total_after if total_before > 0 else 0
        savings_pct = int((saved / total_before) * 100) if total_before > 0 else 0

        # Update UI
        if successful == total and total > 0:
            self.status_icon.configure(text="✅")
            self.title_label.configure(text="Conversion Complete!")
            self.subtitle_label.configure(text="All images converted successfully")
        elif successful > 0:
            self.status_icon.configure(text="⚠️")
            self.title_label.configure(text="Conversion Complete")
            self.subtitle_label.configure(text=f"{successful} of {total} images converted")
        else:
            self.status_icon.configure(text="❌")
            self.title_label.configure(text="Conversion Failed")
            self.subtitle_label.configure(text="No images were converted")

        self.files_count.configure(text=str(successful))
        self.savings_percent.configure(text=f"{savings_pct}%")
        self.before_size.configure(text=self._format_bytes(total_before))
        self.after_size.configure(text=self._format_bytes(total_after))

        # Output folder
        if self.app.output_folder:
            folder_name = self.app.output_folder.name
            self.folder_path.configure(text=folder_name)

    def _open_output_folder(self):
        """Open the output folder in Finder/Explorer."""
        if self.app.output_folder and self.app.output_folder.exists():
            folder = str(self.app.output_folder)

            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", folder])
            else:  # Linux
                subprocess.run(["xdg-open", folder])

    def _convert_more(self):
        """Go back to drop zone to convert more images."""
        self.app.reset_and_go_home()

    def _done(self):
        """Close the application."""
        config.save()
        self.app.destroy()

    def on_show(self, results: List[Dict[str, Any]] = None, **kwargs):
        """Called when this screen is shown."""
        if results:
            self.results = results
            self._update_stats(results)
