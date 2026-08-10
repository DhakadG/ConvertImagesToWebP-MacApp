"""Application shell: window, header, navigation, drag & drop, shortcuts."""

from __future__ import annotations

import platform
import sys
import tkinter
from pathlib import Path

import customtkinter as ctk

from core.config import VERSION, Settings
from core.runner import FileResult, Scan
from gui import theme as t
from gui.screens.home import HomeScreen
from gui.screens.progress import ProgressScreen
from gui.screens.results import ResultsScreen
from gui.widgets import relayout_ring_colors, segmented

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_IMPORTED = True
except Exception:  # optional: the app is fully usable without it
    DND_IMPORTED = False

# tkinterdnd2 grafts drop_target_register/dnd_bind onto tkinter.BaseWidget, but
# tkinter.Tk is not a BaseWidget subclass — so the root window never gets them
# unless DnDWrapper is mixed in explicitly.
if DND_IMPORTED:
    class _Window(ctk.CTk, TkinterDnD.DnDWrapper):
        pass
else:
    _Window = ctk.CTk

IS_MAC = platform.system() == "Darwin"
MOD = "Command" if IS_MAC else "Control"


class App(_Window):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.sources: list[Path] = []
        self.scan: Scan | None = None

        t.apply_appearance(self.settings.theme)
        ctk.set_default_color_theme("blue")

        self.title(f"WebP Studio {VERSION}")
        self.geometry(f"{self.settings.window_width}x{self.settings.window_height}")
        self.minsize(900, 640)
        self.configure(fg_color=t.BG)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_screens()
        self._enable_drag_and_drop()
        self._bind_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show("home")

    # -- chrome ---------------------------------------------------------
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.grid(row=0, column=0, sticky="ew", padx=t.XL, pady=(t.LG, 0))
        header.grid_columnconfigure(1, weight=1)

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(titles, text="WebP Studio", font=t.font(20, "bold"),
                     text_color=t.TEXT).grid(row=0, column=0, sticky="w")
        self.tagline = ctk.CTkLabel(titles, text="Batch image conversion",
                                    font=t.font(11), text_color=t.MUTED)
        self.tagline.grid(row=1, column=0, sticky="w")

        self.theme_buttons = segmented(header, ["System", "Light", "Dark"],
                                       self.settings.theme.capitalize(),
                                       self._set_theme)
        self.theme_buttons.configure(width=210)
        self.theme_buttons.grid(row=0, column=2, sticky="e")

    def _build_screens(self) -> None:
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.screens = {
            "home": HomeScreen(self.container, self),
            "progress": ProgressScreen(self.container, self),
            "results": ResultsScreen(self.container, self),
        }
        self.current = ""

    def show(self, name: str) -> None:
        for screen in self.screens.values():
            screen.grid_remove()
        screen = self.screens[name]
        screen.grid(row=0, column=0, sticky="nsew")
        self.current = name
        if hasattr(screen, "on_show"):
            screen.on_show()

    def _set_theme(self, label: str) -> None:
        self.settings.theme = label.lower()
        t.apply_appearance(self.settings.theme)
        self.settings.save()
        # Rings are raw Canvas drawings; CustomTkinter can't repaint them for us.
        relayout_ring_colors(self)

    # -- drag & drop ----------------------------------------------------
    def _enable_drag_and_drop(self) -> None:
        """Wire tkinterdnd2 if present. v1 shipped a 'drop zone' that could not
        accept a drop; without the package we at least say so."""
        self.dnd_enabled = False
        if not DND_IMPORTED:
            self.tagline.configure(
                text="Batch image conversion · install tkinterdnd2 for drag & drop")
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DropEnter>>", lambda _e: self._highlight(True))
            self.dnd_bind("<<DropLeave>>", lambda _e: self._highlight(False))
            self.dnd_enabled = True
        except Exception as exc:
            # Print it: a silent except here hid the missing DnDWrapper mixin
            # behind a tagline that looked like a normal "not installed" state.
            print(f"drag & drop disabled: {type(exc).__name__}: {exc}", file=sys.stderr)
            self.tagline.configure(
                text="Batch image conversion · drag & drop unavailable on this build")

    def _on_drop(self, event) -> None:
        self._highlight(False)
        if self.current != "home":
            return  # dropping mid-run would silently discard the drop
        paths = [Path(p) for p in self.tk.splitlist(event.data)]
        self.screens["home"].handle_drop(paths)

    def _highlight(self, active: bool) -> None:
        if self.current == "home":
            self.screens["home"].highlight_drop(active)

    # -- shortcuts ------------------------------------------------------
    def _bind_shortcuts(self) -> None:
        self.bind_all(f"<{MOD}-o>", lambda _e: self._if_home(lambda h: h.browse_folder()))
        self.bind_all(f"<{MOD}-Shift-o>", lambda _e: self._if_home(lambda h: h.browse_files()))
        self.bind_all("<Return>", lambda _e: self._if_home(lambda h: h.start()))
        self.bind_all("<Escape>", lambda _e: self._escape())

    def _is_typing(self) -> bool:
        """CustomTkinter wraps a real tkinter.Entry, and focus_get() returns
        that inner widget — so checking for "CTkEntry" never matched and Return
        started a conversion while you were still typing a value."""
        return isinstance(self.focus_get(), (tkinter.Entry, tkinter.Text))

    def _if_home(self, action) -> None:
        if self.current == "home" and not self._is_typing():
            action(self.screens["home"])

    def _escape(self) -> None:
        if self.current == "progress":
            self.screens["progress"].cancel()
        elif self.current == "results":
            self.go_home()
        elif self.current == "home":
            self.screens["home"].clear_sources()

    # -- flow -----------------------------------------------------------
    def begin_conversion(self, scan: Scan) -> None:
        self.show("progress")
        self.screens["progress"].start(scan)

    def finish_conversion(self, results: list[FileResult], cancelled: bool,
                          elapsed: float) -> None:
        self.show("results")
        self.screens["results"].show(results, cancelled, elapsed)

    def go_home(self) -> None:
        self.show("home")

    def on_close(self) -> None:
        progress = self.screens.get("progress")
        if progress and progress.runner and not progress.runner.cancelled:
            progress.runner.cancel()  # don't leave workers writing after the window dies
        self.settings.window_width = self.winfo_width()
        self.settings.window_height = self.winfo_height()
        self.settings.save()
        self.destroy()


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
