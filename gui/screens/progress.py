"""Progress: ring, live counters, ETA, rolling log.

The runner calls back from worker threads; everything here goes through a
queue and one `after` poll, because Tk is not thread-safe.
"""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.runner import (CANCELLED, CONVERTED, FAILED, SKIPPED, FileResult, Progress,
                         Runner, Scan, format_bytes, format_duration)
from gui import theme as t
from gui.widgets import Card, LogView, ProgressRing, StatTile, ghost_button

if TYPE_CHECKING:
    from gui.app import App

POLL_MS = 80
STATUS_MARK = {CONVERTED: "ok  ", SKIPPED: "skip", FAILED: "FAIL", CANCELLED: "----"}


class ProgressScreen(ctk.CTkFrame):
    def __init__(self, parent, app: "App"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.runner: Runner | None = None
        self.thread = None
        self.events: queue.Queue = queue.Queue()
        self._polling = False
        self._last: Progress | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    # -- layout ---------------------------------------------------------
    def _build(self) -> None:
        top = Card(self, "Converting")
        top.grid(row=0, column=0, sticky="ew", padx=t.XL, pady=(t.LG, t.MD))
        body = top.body()
        body.grid_columnconfigure(0, weight=0)  # ring keeps its natural width
        body.grid_columnconfigure(1, weight=1)  # tiles take the rest

        self.ring = ProgressRing(body, size=168)
        self.ring.grid(row=0, column=0, rowspan=2, padx=(t.SM, t.XL))

        tiles = ctk.CTkFrame(body, fg_color="transparent")
        tiles.grid(row=0, column=1, sticky="ew")
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tile")

        self.tile_done = StatTile(tiles, "Converted", "0", t.SUCCESS)
        self.tile_saved = StatTile(tiles, "Saved so far", "—", t.SUCCESS)
        self.tile_eta = StatTile(tiles, "Time left", "—")
        self.tile_issues = StatTile(tiles, "Skipped / failed", "0 / 0", t.MUTED)
        for i, tile in enumerate((self.tile_done, self.tile_saved, self.tile_eta,
                                  self.tile_issues)):
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else t.SM, 0))

        self.current = ctk.CTkLabel(body, text="", font=t.font(11), text_color=t.MUTED,
                                    anchor="w")
        self.current.grid(row=1, column=1, sticky="sw", pady=(t.MD, 0))

        log_card = Card(self, "Activity")
        log_card.grid(row=1, column=0, sticky="nsew", padx=t.XL, pady=(0, t.MD))
        log_body = log_card.body()
        log_body.grid_rowconfigure(0, weight=1)
        self.log = LogView(log_body)
        self.log.grid(row=0, column=0, sticky="nsew")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=t.XL, pady=(0, t.LG))
        bar.grid_columnconfigure(0, weight=1)
        self.elapsed = ctk.CTkLabel(bar, text="", font=t.font(12), text_color=t.MUTED,
                                    anchor="w")
        self.elapsed.grid(row=0, column=0, sticky="w")
        self.cancel_button = ctk.CTkButton(bar, text="Stop", command=self.cancel,
                                           height=40, width=140, font=t.font(13, "bold"),
                                           corner_radius=t.RADIUS_SM,
                                           fg_color=t.SURFACE_ALT, hover_color=t.DANGER,
                                           text_color=t.TEXT, border_width=1,
                                           border_color=t.BORDER)
        self.cancel_button.grid(row=0, column=1, sticky="e")

    # -- lifecycle ------------------------------------------------------
    def start(self, scan: Scan) -> None:
        self.log.clear()
        self.ring.set(0, f"of {len(scan.files):,}")
        self.tile_done.set("0")
        self.tile_saved.set("—")
        self.tile_eta.set("—")
        self.tile_issues.set("0 / 0")
        self.current.configure(text="")
        self.elapsed.configure(text="")
        self.cancel_button.configure(text="Stop", state="normal")
        self._last = None

        self.events = queue.Queue()
        self.runner = Runner(
            scan, self.app.settings,
            on_progress=lambda p: self.events.put(("progress", p)),
            on_file=lambda r: self.events.put(("file", r)),
            on_finish=lambda results, cancelled, elapsed:
                self.events.put(("finish", (results, cancelled, elapsed))),
        )
        # kept so the window can wait for it on close
        self.thread = self.runner.start_background()

        if not self._polling:
            self._polling = True
            self._poll()

    def cancel(self) -> None:
        if self.runner:
            self.runner.cancel()
        self.cancel_button.configure(text="Stopping…", state="disabled")

    # -- event pump -----------------------------------------------------
    def _poll(self) -> None:
        latest: Progress | None = None
        finish = None
        try:
            # Drain fully each tick and render only the newest progress value —
            # at 16 workers the queue fills faster than the UI can redraw.
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    latest = payload
                elif kind == "file":
                    self._log_file(payload)
                elif kind == "finish":
                    finish = payload
        except queue.Empty:
            pass

        if latest:
            self._render(latest)
        if finish:
            self._polling = False
            results, cancelled, elapsed = finish
            self.app.finish_conversion(results, cancelled, elapsed)
            return
        self.after(POLL_MS, self._poll)

    def _render(self, p: Progress) -> None:
        self._last = p
        self.ring.set(p.fraction, f"{p.completed:,} of {p.total:,}")
        self.tile_done.set(f"{p.converted:,}")
        saved = p.bytes_in - p.bytes_out
        self.tile_saved.set(format_bytes(saved) if saved > 0 else "—")
        eta = p.eta_seconds
        self.tile_eta.set(format_duration(eta) if eta is not None else "—")
        self.tile_issues.set(f"{p.skipped:,} / {p.failed:,}")
        self.current.configure(text=p.current)
        rate = f" · {p.rate:.1f} img/s" if p.rate else ""
        self.elapsed.configure(text=f"Elapsed {format_duration(p.elapsed)}{rate}")

    def _log_file(self, result: FileResult) -> None:
        mark = STATUS_MARK.get(result.status, "?")
        detail = ""
        if result.status == CONVERTED:
            detail = f"{format_bytes(result.source_bytes)} → {format_bytes(result.output_bytes)}"
            if result.message:
                detail += f"  ({result.message})"
        elif result.message:
            detail = result.message
        self.log.append(f"{mark}  {result.source.name:<44.44} {detail}")
