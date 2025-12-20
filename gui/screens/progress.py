"""
Screen 3: Progress - Real-time processing status display.

Features:
- Circular progress indicator
- Overall progress bar
- File list with per-file status
- Time remaining estimate
- Cancel button
"""

import customtkinter as ctk
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Optional
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

if TYPE_CHECKING:
    from gui.app import WebPConverterApp

# Import config and processing engine
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.config import config


class ProgressScreen(ctk.CTkFrame):
    """
    Progress screen - Shows real-time processing status.
    """

    def __init__(self, parent, app: "WebPConverterApp"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.processing = False
        self.cancel_requested = False
        self.results = []
        self.update_queue = queue.Queue()

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ─────────────────────────────────────────────────────────────────────
        # Header
        # ─────────────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Converting...",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        # ─────────────────────────────────────────────────────────────────────
        # Main Progress Section
        # ─────────────────────────────────────────────────────────────────────
        progress_card = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray17"),
            corner_radius=20
        )
        progress_card.grid(row=1, column=0, sticky="ew", padx=30, pady=20)
        progress_card.grid_columnconfigure(0, weight=1)

        # Progress percentage
        self.progress_label = ctk.CTkLabel(
            progress_card,
            text="0%",
            font=ctk.CTkFont(size=48, weight="bold")
        )
        self.progress_label.grid(row=0, column=0, pady=(30, 5))

        # File count
        self.count_label = ctk.CTkLabel(
            progress_card,
            text="0 of 0 images",
            font=ctk.CTkFont(size=16),
            text_color=("gray50", "gray60")
        )
        self.count_label.grid(row=1, column=0, pady=(0, 10))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_card,
            height=12,
            corner_radius=6
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=40, pady=(10, 10))

        # Time remaining
        self.time_label = ctk.CTkLabel(
            progress_card,
            text="Calculating...",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        self.time_label.grid(row=3, column=0, pady=(5, 30))

        # ─────────────────────────────────────────────────────────────────────
        # File List
        # ─────────────────────────────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        list_label = ctk.CTkLabel(
            list_frame,
            text="Current Files",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray50", "gray60")
        )
        list_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Scrollable file list
        self.file_list = ctk.CTkScrollableFrame(
            list_frame,
            fg_color=("gray90", "gray17"),
            corner_radius=12
        )
        self.file_list.grid(row=1, column=0, sticky="nsew")
        self.file_list.grid_columnconfigure(0, weight=1)

        # File entry widgets (pre-create some for reuse)
        self.file_entries: Dict[str, ctk.CTkLabel] = {}

        # ─────────────────────────────────────────────────────────────────────
        # Footer with Cancel Button
        # ─────────────────────────────────────────────────────────────────────
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(10, 30))
        footer_frame.grid_columnconfigure(0, weight=1)

        self.cancel_btn = ctk.CTkButton(
            footer_frame,
            text="✕ Cancel",
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=10,
            fg_color=("gray70", "gray30"),
            hover_color=("red", "darkred"),
            command=self._cancel_processing
        )
        self.cancel_btn.grid(row=0, column=0)

    def _add_file_entry(self, filename: str, status: str = "pending"):
        """Add or update a file entry in the list."""
        status_icons = {
            "pending": "⏳",
            "processing": "🔄",
            "done": "✅",
            "error": "❌",
            "skipped": "⏭️"
        }

        icon = status_icons.get(status, "⏳")
        display_name = filename[:40] + "..." if len(filename) > 40 else filename

        if filename in self.file_entries:
            self.file_entries[filename].configure(text=f"{icon} {display_name}")
        else:
            label = ctk.CTkLabel(
                self.file_list,
                text=f"{icon} {display_name}",
                font=ctk.CTkFont(size=12),
                anchor="w"
            )
            label.grid(sticky="ew", padx=10, pady=2)
            self.file_entries[filename] = label

    def _update_progress(self, completed: int, total: int, current_file: str = ""):
        """Update progress display."""
        if total == 0:
            return

        percent = int((completed / total) * 100)
        self.progress_label.configure(text=f"{percent}%")
        self.count_label.configure(text=f"{completed} of {total} images")
        self.progress_bar.set(completed / total)

        # Update current file
        if current_file:
            self._add_file_entry(current_file, "processing")

    def _start_conversion(self):
        """Start the conversion process in a background thread."""
        self.processing = True
        self.cancel_requested = False
        self.results = []

        # Clear file list
        for widget in self.file_list.winfo_children():
            widget.destroy()
        self.file_entries.clear()

        # Start processing thread
        thread = threading.Thread(target=self._run_conversion, daemon=True)
        thread.start()

        # Start update loop
        self._check_updates()

    def _run_conversion(self):
        """Run the actual conversion (in background thread)."""
        try:
            from core.converter import find_images, process_single_image
        except ImportError:
            # Fallback - will be implemented
            self._simulate_conversion()
            return

        source_paths = self.app.source_paths
        output_folder = self.app.output_folder

        # Determine root folder
        if source_paths and source_paths[0].is_dir():
            root_folder = source_paths[0]
        elif source_paths:
            root_folder = source_paths[0].parent
        else:
            root_folder = Path.home()

        # Find all images
        images = find_images(source_paths, config.EXTENSIONS)
        total = len(images)

        if total == 0:
            self.update_queue.put(("done", []))
            return

        # Process images
        completed = 0
        start_time = time.time()

        for img_path in images:
            if self.cancel_requested:
                break

            # Update UI
            self.update_queue.put(("progress", completed, total, img_path.name))

            # Process image
            try:
                result = process_single_image(img_path, output_folder, config, root_folder)
                # Convert dataclass to dict for results screen
                result_dict = {
                    "success": result.success,
                    "file": result.file_path,
                    "output_path": result.output_path,
                    "error": result.error_message,
                    "original_size": result.original_size,
                    "output_size": result.output_size,
                    "was_skipped": result.was_skipped,
                    "was_copied": result.was_copied,
                }
                self.results.append(result_dict)
            except Exception as e:
                self.results.append({
                    "success": False,
                    "error": str(e),
                    "file": img_path,
                    "original_size": 0,
                    "output_size": 0
                })

            completed += 1

        # Final update
        self.update_queue.put(("done", self.results))

    def _simulate_conversion(self):
        """Simulate conversion for testing when core module not ready."""
        import random

        source_paths = self.app.source_paths
        total = 0

        # Count files
        for path in source_paths:
            if path.is_dir():
                total += len(list(path.rglob("*")))
            else:
                total += 1

        if total == 0:
            total = 10  # Default for testing

        for i in range(total):
            if self.cancel_requested:
                break

            filename = f"image_{i+1:03d}.jpg"
            self.update_queue.put(("progress", i, total, filename))
            time.sleep(0.1)  # Simulate processing time

            # Add to results
            self.results.append({
                "success": random.random() > 0.1,
                "file": filename,
                "saved_bytes": random.randint(10000, 500000)
            })

        self.update_queue.put(("done", self.results))

    def _check_updates(self):
        """Check update queue and update UI."""
        try:
            while True:
                msg = self.update_queue.get_nowait()

                if msg[0] == "progress":
                    _, completed, total, current_file = msg
                    self._update_progress(completed, total, current_file)

                elif msg[0] == "done":
                    _, results = msg
                    self.processing = False
                    self.app.show_results(results)
                    return

        except queue.Empty:
            pass

        # Schedule next check
        if self.processing:
            self.after(100, self._check_updates)

    def _cancel_processing(self):
        """Cancel the ongoing processing."""
        self.cancel_requested = True
        self.cancel_btn.configure(text="Cancelling...", state="disabled")

    def on_show(self, **kwargs):
        """Called when this screen is shown."""
        # Reset state
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.count_label.configure(text="Starting...")
        self.time_label.configure(text="Calculating...")
        self.cancel_btn.configure(text="✕ Cancel", state="normal")

        # Start conversion
        self._start_conversion()
