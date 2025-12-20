"""
Main Application Window for ConvertImagesToWebP - MacAlpha v0.1

This is the main entry point for the GUI app. It manages:
- Window creation and theming
- Screen navigation (Drop Zone → Settings → Progress → Results)
- Global state management
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional, List, Callable
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import config, AppConfig
from gui.screens.dropzone import DropZoneScreen
from gui.screens.settings import SettingsScreen
from gui.screens.progress import ProgressScreen
from gui.screens.results import ResultsScreen


class WebPConverterApp(ctk.CTk):
    """
    Main application window for ConvertImagesToWebP MacAlpha.

    Manages screen navigation and global state.
    """

    VERSION = "0.1.0"
    APP_NAME = "ConvertImagesToWebP - MacAlpha"

    def __init__(self):
        super().__init__()

        # Configure window
        self.title(self.APP_NAME)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(500, 600)

        # Set theme
        ctk.set_appearance_mode(config.THEME)
        ctk.set_default_color_theme("blue")

        # State management
        self.source_paths: List[Path] = []
        self.output_folder: Optional[Path] = None
        self.processing_results: List = []

        # Screen container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=0, pady=0)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Initialize screens (lazy loading pattern)
        self.screens = {}
        self.current_screen = None

        # Show initial screen
        self.show_screen("dropzone")

        # Bind window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def show_screen(self, screen_name: str, **kwargs) -> None:
        """
        Navigate to a specific screen.

        Args:
            screen_name: One of 'dropzone', 'settings', 'progress', 'results'
            **kwargs: Additional arguments to pass to the screen
        """
        # Create screen if not exists
        if screen_name not in self.screens:
            self.screens[screen_name] = self._create_screen(screen_name)

        # Hide current screen
        if self.current_screen:
            self.current_screen.pack_forget()

        # Show new screen
        screen = self.screens[screen_name]
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

        # Update screen with any passed data
        if hasattr(screen, "on_show"):
            screen.on_show(**kwargs)

    def _create_screen(self, screen_name: str) -> ctk.CTkFrame:
        """Create a screen instance by name."""
        screen_classes = {
            "dropzone": DropZoneScreen,
            "settings": SettingsScreen,
            "progress": ProgressScreen,
            "results": ResultsScreen,
        }

        screen_class = screen_classes.get(screen_name)
        if screen_class:
            return screen_class(self.container, app=self)
        else:
            raise ValueError(f"Unknown screen: {screen_name}")

    def set_source_paths(self, paths: List[Path]) -> None:
        """Set the source paths to process."""
        self.source_paths = paths

        # Determine output folder
        if paths:
            if paths[0].is_dir():
                self.output_folder = paths[0] / config.OUTPUT_FOLDER
            else:
                self.output_folder = paths[0].parent / config.OUTPUT_FOLDER

    def start_processing(self) -> None:
        """Navigate to progress screen and start processing."""
        self.show_screen("progress")

    def show_results(self, results: List) -> None:
        """Navigate to results screen with processing results."""
        self.processing_results = results
        self.show_screen("results", results=results)

    def reset_and_go_home(self) -> None:
        """Reset state and go back to drop zone."""
        self.source_paths = []
        self.output_folder = None
        self.processing_results = []
        self.show_screen("dropzone")

    def on_close(self) -> None:
        """Handle window close event."""
        # Save window geometry to config
        config.WINDOW_WIDTH = self.winfo_width()
        config.WINDOW_HEIGHT = self.winfo_height()
        config.save()

        self.destroy()


def main():
    """Main entry point."""
    app = WebPConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
