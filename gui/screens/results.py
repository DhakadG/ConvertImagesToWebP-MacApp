"""Results: what happened, what went wrong, and where the files went.

v1 reported "Conversion Complete!" even after a cancel, and errors were
recorded but never shown. Both are visible here.
"""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.runner import (CANCELLED, CONVERTED, FAILED, SKIPPED, FileResult,
                         format_bytes, format_duration)
from gui import theme as t
from gui.widgets import Card, LogView, StatTile, ghost_button, primary_button

if TYPE_CHECKING:
    from gui.app import App


class ResultsScreen(ctk.CTkFrame):
    def __init__(self, parent, app: "App"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.results: list[FileResult] = []
        self.output_folder: Path | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()

    def _build(self) -> None:
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=t.XL, pady=(t.XL, t.MD))
        head.grid_columnconfigure(0, weight=1)
        self.headline = ctk.CTkLabel(head, text="", font=t.font(26, "bold"),
                                     text_color=t.TEXT, anchor="w")
        self.headline.grid(row=0, column=0, sticky="w")
        self.subhead = ctk.CTkLabel(head, text="", font=t.font(13), text_color=t.MUTED,
                                    anchor="w")
        self.subhead.grid(row=1, column=0, sticky="w", pady=(2, 0))

        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.grid(row=1, column=0, sticky="ew", padx=t.XL)
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tile")
        self.tile_files = StatTile(tiles, "Images converted", "0")
        self.tile_saved = StatTile(tiles, "Space saved", "—", t.SUCCESS)
        # Smaller type: "1.2 GB → 240.0 MB" overflows the tile at 24pt.
        self.tile_sizes = StatTile(tiles, "Before → after", "—", value_size=17)
        self.tile_time = StatTile(tiles, "Took", "—")
        for i, tile in enumerate((self.tile_files, self.tile_saved, self.tile_sizes,
                                  self.tile_time)):
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else t.SM, 0))

        self.detail_card = Card(self, "Details")
        self.detail_card.grid(row=2, column=0, sticky="nsew", padx=t.XL, pady=t.MD)
        detail_body = self.detail_card.body()
        detail_body.grid_rowconfigure(0, weight=1)
        self.detail = LogView(detail_body)
        self.detail.grid(row=0, column=0, sticky="nsew")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=t.XL, pady=(0, t.LG))
        bar.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ghost_button(left, "Open output folder", self.open_output, height=42,
                     width=170).grid(row=0, column=0, padx=(0, t.SM))
        self.save_log_button = ghost_button(left, "Save log…", self.save_log, height=42,
                                            width=120)
        self.save_log_button.grid(row=0, column=1)
        more = primary_button(bar, "Convert more", self.app.go_home, height=42)
        more.configure(width=170)
        more.grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------------
    def show(self, results: list[FileResult], cancelled: bool, elapsed: float) -> None:
        self.results = results
        converted = [r for r in results if r.status == CONVERTED]
        skipped = [r for r in results if r.status == SKIPPED]
        failed = [r for r in results if r.status == FAILED]
        stopped = [r for r in results if r.status == CANCELLED]

        bytes_in = sum(r.source_bytes for r in converted)
        bytes_out = sum(r.output_bytes for r in converted)
        saved = bytes_in - bytes_out

        # Every branch names all three outcomes it knows about. Reporting
        # "all 1 images failed" while quietly ignoring 14 skips is how you get
        # a user who thinks the app is broken when it did exactly the right thing.
        parts = []
        if skipped:
            parts.append(f"{len(skipped):,} already existed")
        if failed:
            parts.append(f"{len(failed):,} failed")
        tail = (" · " + " · ".join(parts)) if parts else ""

        if cancelled:
            self.headline.configure(text="Stopped", text_color=t.WARNING)
            self.subhead.configure(text=f"{len(converted):,} converted before you stopped"
                                        f" · {len(stopped):,} never started{tail}")
        elif failed and converted:
            self.headline.configure(text="Finished with errors", text_color=t.WARNING)
            self.subhead.configure(text=f"{len(converted):,} converted{tail}")
        elif failed:
            self.headline.configure(text="Nothing converted", text_color=t.DANGER)
            self.subhead.configure(text=f"{len(failed):,} failed"
                                        + (f" · {len(skipped):,} already existed"
                                           if skipped else "") + " — see details")
        elif converted:
            self.headline.configure(text="Done", text_color=t.SUCCESS)
            self.subhead.configure(text=f"{len(converted):,} images converted{tail}")
        else:
            self.headline.configure(text="Nothing to do", text_color=t.MUTED)
            self.subhead.configure(
                text=f"All {len(skipped):,} images already existed — set "
                     f"“If a file already exists” to Overwrite to redo them"
                if skipped else "No images were processed")

        self.tile_files.set(f"{len(converted):,}")
        percent = round(saved / bytes_in * 100) if bytes_in else 0
        self.tile_saved.set(f"{percent}%" if saved > 0 else "—")
        self.tile_sizes.set(f"{format_bytes(bytes_in)} → {format_bytes(bytes_out)}"
                            if converted else "—")
        self.tile_time.set(format_duration(elapsed))

        self.output_folder = next((r.destination.parent for r in converted
                                   if r.destination), None)
        self._render_detail(converted, skipped, failed, saved)

    def _render_detail(self, converted, skipped, failed, saved: int) -> None:
        self.detail.clear()
        if saved > 0:
            self.detail.append(f"Saved {format_bytes(saved)} across {len(converted):,} images.")
        if self.output_folder:
            self.detail.append(f"Output: {self.output_folder}")
        if converted or skipped or failed:
            self.detail.append("")

        # Problems first — that is what the user came to this screen for.
        for r in failed:
            self.detail.append(f"FAIL  {r.source.name:<40.40} {r.message}")
        for r in skipped:
            self.detail.append(f"skip  {r.source.name:<40.40} {r.message}")
        notes = [r for r in converted if r.message]
        for r in notes:
            self.detail.append(f"note  {r.source.name:<40.40} {r.message}")

        if not (failed or skipped or notes):
            self.detail.append("No warnings. Every image converted cleanly.")

    # ------------------------------------------------------------------
    def open_output(self) -> None:
        folder = self.output_folder
        if not folder:
            self.detail.append("\nNo output folder — nothing was written this run.")
            return
        if not folder.exists():
            self.detail.append(f"\nOutput folder is gone: {folder}")
            return
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", str(folder)], check=False)
        elif system == "Windows":
            subprocess.run(["explorer", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)

    def save_log(self) -> None:
        default = f"conversion-log-{datetime.now():%Y%m%d-%H%M}.txt"
        target = filedialog.asksaveasfilename(defaultextension=".txt",
                                              initialfile=default,
                                              filetypes=[("Text file", "*.txt")])
        if not target:
            return
        lines: list[str] = []
        for r in self.results:
            row = f"{r.status.upper():<10} {r.source}"
            if r.destination:
                row += f" -> {r.destination} ({format_bytes(r.source_bytes)} -> {format_bytes(r.output_bytes)})"
            if r.message:
                row += f"  [{r.message}]"
            lines.append(row)
        try:
            Path(target).write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            # Read-only location, full disk, revoked permission — telling the
            # user beats a traceback into a console they cannot see.
            self.detail.append(f"\nCould not save the log: {exc}")
            self.save_log_button.configure(text="Save failed")
        else:
            self.save_log_button.configure(text="Saved ✓")
        self.after(2200, lambda: self.save_log_button.configure(text="Save log…"))
