"""Home: drop zone on the left, live settings on the right, one action bar.

v1 spread this over two wizard screens, so you could never see your files and
your settings at the same time.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.config import SOURCE_EXTENSIONS
from core.imaging import readable_extensions
from core.runner import Scan, destination_root, format_bytes, scan_sources
from gui import theme as t
from gui.panel import SettingsPanel
from gui.widgets import Card, ghost_button, primary_button

if TYPE_CHECKING:
    from gui.app import App

FILE_TYPES = [
    ("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.avif *.heic *.heif *.gif"),
    ("All files", "*.*"),
]

PANEL_WIDTH = 372
SCAN_POLL_MS = 60


class HomeScreen(ctk.CTkFrame):
    def __init__(self, parent, app: "App"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.scan: Scan | None = None
        self._scan_token = 0
        self._scan_results: queue.Queue = queue.Queue()
        self._scan_pending = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=PANEL_WIDTH + t.MD)
        self.grid_rowconfigure(0, weight=1)

        self._build_left()
        self._build_panel()
        self._build_action_bar()
        self._render_sources()

    # -- layout ---------------------------------------------------------
    def _build_left(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(t.XL, t.MD), pady=(t.LG, 0))

        # pack, not grid: `expand=True` fills the column unambiguously, where a
        # weighted grid row here left the card at its requested height.
        self.drop_card = ctk.CTkFrame(left, fg_color=t.SURFACE, corner_radius=t.RADIUS,
                                      border_width=2, border_color=t.BORDER_STRONG)
        self.drop_card.pack(fill="both", expand=True)
        self.drop_card.grid_columnconfigure(0, weight=1)
        self.drop_card.grid_rowconfigure(0, weight=1)

        self.drop_inner = ctk.CTkFrame(self.drop_card, fg_color="transparent")
        self.drop_inner.place(relx=0.5, rely=0.5, anchor="center")

        self.drop_icon = ctk.CTkLabel(self.drop_inner, text="⤓", font=t.font(56, "bold"),
                                      text_color=t.BORDER_STRONG)
        self.drop_icon.pack()
        self.drop_title = ctk.CTkLabel(self.drop_inner, text="Drop images or folders",
                                       font=t.font(19, "bold"), text_color=t.TEXT)
        self.drop_title.pack(pady=(t.SM, 2))
        self.drop_subtitle = ctk.CTkLabel(self.drop_inner, text="Folders are searched recursively",
                                          font=t.font(12), text_color=t.MUTED)
        self.drop_subtitle.pack(pady=(0, t.LG))

        buttons = ctk.CTkFrame(self.drop_inner, fg_color="transparent")
        buttons.pack()
        ghost_button(buttons, "Choose folder", self.browse_folder, height=38,
                     width=140).grid(row=0, column=0, padx=t.XS)
        ghost_button(buttons, "Choose files", self.browse_files, height=38,
                     width=140).grid(row=0, column=1, padx=t.XS)

        # height=1: an empty CTkFrame defaults to 200px, which silently stole
        # a third of the drop zone whenever there were no recent folders.
        self.formats_hint = ctk.CTkLabel(
            self.drop_card, text=_supported_line(), font=t.font(11), text_color=t.FAINT)
        self.formats_hint.place(relx=0.5, rely=1.0, y=-t.MD, anchor="s")

        self.recent_bar = ctk.CTkFrame(left, fg_color="transparent", height=1)
        self.recent_bar.pack(fill="x", pady=(t.SM, 0))
        self._render_recent()

        # Clicking anywhere in the empty drop area opens the folder picker.
        for widget in (self.drop_card, self.drop_inner, self.drop_icon,
                       self.drop_title, self.drop_subtitle):
            widget.bind("<Button-1>", lambda _e: self._click_drop_area())

    def _build_panel(self) -> None:
        holder = ctk.CTkFrame(self, fg_color="transparent", width=PANEL_WIDTH)
        holder.grid(row=0, column=1, sticky="nsew", padx=(0, t.XL), pady=(t.LG, 0))
        holder.pack_propagate(False)
        self.panel = SettingsPanel(holder, self.app.settings, self._settings_changed)
        self.panel.pack(fill="both", expand=True)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=t.XL, pady=t.LG)
        bar.grid_columnconfigure(0, weight=1)

        self.summary = ctk.CTkLabel(bar, text="No files selected", font=t.font(12),
                                    text_color=t.MUTED, anchor="w", justify="left")
        self.summary.grid(row=0, column=0, sticky="w")

        self.convert_button = primary_button(bar, "Convert", self.start, height=46)
        self.convert_button.configure(width=190, state="disabled")
        self.convert_button.grid(row=0, column=1, sticky="e", padx=(t.MD, 0))

    def _render_recent(self) -> None:
        for child in self.recent_bar.winfo_children():
            child.destroy()
        folders = [Path(p) for p in self.app.settings.recent_folders[:4]]
        folders = [f for f in folders if f.exists()]
        if not folders:
            return
        ctk.CTkLabel(self.recent_bar, text="Recent", font=t.font(11),
                     text_color=t.FAINT).grid(row=0, column=0, padx=(2, t.SM))
        for i, folder in enumerate(folders):
            ghost_button(self.recent_bar, folder.name,
                         lambda f=folder: self.set_sources([f]),
                         height=28).grid(row=0, column=i + 1, padx=2)

    # -- source selection ------------------------------------------------
    def _click_drop_area(self) -> None:
        if self.app.sources:
            self.clear_sources()
        else:
            self.browse_folder()

    def browse_folder(self) -> None:
        initial = self.app.settings.recent_folders[0] if self.app.settings.recent_folders else str(Path.home())
        chosen = filedialog.askdirectory(title="Choose a folder of images",
                                         initialdir=initial)
        if chosen:
            self.set_sources([Path(chosen)])

    def browse_files(self) -> None:
        chosen = filedialog.askopenfilenames(title="Choose images", filetypes=FILE_TYPES,
                                             initialdir=str(Path.home()))
        if chosen:
            self.set_sources([Path(p) for p in chosen])

    def set_sources(self, paths: list[Path]) -> None:
        paths = [p for p in paths if p.exists()]
        if not paths:
            return
        self.app.sources = paths
        folder = paths[0] if paths[0].is_dir() else paths[0].parent
        self.app.settings.add_recent_folder(folder)
        self._render_recent()
        self._render_sources()
        self._rescan()

    def clear_sources(self) -> None:
        self.app.sources = []
        self.scan = None
        self._scan_token += 1  # invalidate any in-flight scan
        self._scan_pending = False
        self._render_sources()
        self._update_summary("No files selected", ready=False)

    def handle_drop(self, paths: list[Path]) -> None:
        self.set_sources(paths)

    # -- preflight scan --------------------------------------------------
    def _rescan(self) -> None:
        """Count files off the Tk thread — a network folder with 40k files
        would otherwise freeze the window while it walks."""
        self._scan_token += 1
        token = self._scan_token
        self._scan_pending = True
        sources = list(self.app.sources)
        settings = self.app.settings
        self._update_summary("Scanning…", ready=False)

        def work() -> None:
            exclude = destination_root(sources, settings)
            scan = scan_sources(sources, readable_extensions(SOURCE_EXTENSIONS), exclude)
            self._scan_results.put((token, scan))

        threading.Thread(target=work, daemon=True).start()
        # Hand the result back through a queue the main thread polls. Calling
        # `after()` from the worker reaches into Tk from the wrong thread.
        self.after(SCAN_POLL_MS, self._poll_scan)

    def _poll_scan(self) -> None:
        try:
            token, scan = self._scan_results.get_nowait()
        except queue.Empty:
            if self._scan_pending:
                self.after(SCAN_POLL_MS, self._poll_scan)
            return
        self._scan_done(token, scan)
        if self._scan_pending:
            self.after(SCAN_POLL_MS, self._poll_scan)  # that was a stale result

    def _scan_done(self, token: int, scan: Scan) -> None:
        if token != self._scan_token:
            return  # a newer scan superseded this one; keep polling for it
        self._scan_pending = False
        self.scan = scan
        self.app.scan = scan
        if not scan.files:
            self._update_summary("No convertible images found here", ready=False)
            return
        target = destination_root(self.app.sources, self.app.settings)
        where = "beside each original" if target is None else _shorten(target)
        self._update_summary(
            f"{len(scan.files):,} images · {format_bytes(scan.total_bytes)}\n→ {where}",
            ready=True)

    def _update_summary(self, text: str, ready: bool) -> None:
        self.summary.configure(text=text)
        count = len(self.scan.files) if (ready and self.scan) else 0
        self.convert_button.configure(
            state="normal" if ready else "disabled",
            text=f"Convert {count:,} images" if count else "Convert")

    def _settings_changed(self) -> None:
        self.app.settings.save()
        if self.app.sources:
            self._rescan()  # destination and exclusions may have moved

    # -- selected-state rendering ----------------------------------------
    def _render_sources(self) -> None:
        selected = bool(self.app.sources)
        if not selected:
            self.drop_icon.configure(text="⤓", text_color=t.BORDER_STRONG)
            self.drop_title.configure(text="Drop images or folders")
            self.drop_subtitle.configure(text="Folders are searched recursively")
            self.drop_card.configure(border_color=t.BORDER_STRONG)
            return

        names = [p.name for p in self.app.sources[:3]]
        extra = len(self.app.sources) - len(names)
        listing = ", ".join(names) + (f" +{extra} more" if extra > 0 else "")
        self.drop_icon.configure(text="✓", text_color=t.ACCENT)
        self.drop_title.configure(text=_ellipsize(listing, 46))
        self.drop_subtitle.configure(text="Click here to clear · or drop something else")
        self.drop_card.configure(border_color=t.ACCENT)

    def highlight_drop(self, active: bool) -> None:
        self.drop_card.configure(border_color=t.ACCENT if active else
                                 (t.ACCENT if self.app.sources else t.BORDER_STRONG))

    # -- go --------------------------------------------------------------
    def start(self) -> None:
        if self.scan and self.scan.files:
            self.app.settings.save()
            self.app.begin_conversion(self.scan)

    def on_show(self) -> None:
        self.panel._reload_controls()
        self._render_recent()
        if self.app.sources:
            self._rescan()


def _supported_line() -> str:
    """Advertise only what this install can actually read — HEIC disappears
    from the list when pillow-heif isn't there, instead of failing at file 1."""
    names = [e[1:].upper() for e in readable_extensions(SOURCE_EXTENSIONS)]
    names = [n for n in names if n not in ("JPEG", "TIF", "HEIF")]
    return "Reads " + " · ".join(names)


def _shorten(path: Path) -> str:
    try:
        return str(path.relative_to(Path.home()).as_posix())
    except ValueError:
        return _ellipsize(str(path), 52)


def _ellipsize(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
