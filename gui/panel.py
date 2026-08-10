"""The settings panel that lives beside the drop zone on the home screen.

v1 made settings a separate wizard step, so you couldn't see what you'd
selected while choosing how to convert it. This is the same options, live,
next to the files.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from core.config import PRESET_HINTS, PRESETS, Settings
from core.imaging import available_output_formats
from gui import theme as t
from gui.widgets import (Card, SliderRow, ghost_button, option_menu, section_label,
                         segmented, switch)

RESIZE_LABELS = {
    "none": "No limit",
    "long_edge": "Longest edge",
    "width": "Max width",
    "height": "Max height",
    "megapixels": "Max megapixels",
}
RESIZE_BY_LABEL = {v: k for k, v in RESIZE_LABELS.items()}

DEST_LABELS = {
    "subfolder": "Subfolder beside originals",
    "custom": "Choose a folder…",
    "in_place": "Next to each original",
}
DEST_BY_LABEL = {v: k for k, v in DEST_LABELS.items()}

THREAD_LABELS = ["Auto", "1", "2", "4", "8", "16"]


class SettingsPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings: Settings, on_change: Callable[[], None]):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.settings = settings
        self.on_change = on_change
        self.grid_columnconfigure(0, weight=1)
        self._row = 0
        self._building = True

        self._build_preset()
        self._build_encoding()
        self._build_geometry()
        self._build_metadata()
        self._build_destination()

        self._building = False
        self._sync_conditional_rows()

    # -- helpers --------------------------------------------------------
    def _add(self, widget, pady=(0, t.MD)) -> None:
        # right padding keeps cards clear of the scrollbar
        widget.grid(row=self._row, column=0, sticky="ew", padx=(0, t.SM), pady=pady)
        self._row += 1

    def _changed(self, refresh_preset: bool = True) -> None:
        if self._building:
            return
        self.settings.clamp()
        if refresh_preset:
            self._refresh_preset_label()
        self._sync_conditional_rows()
        self.on_change()

    # -- presets --------------------------------------------------------
    def _build_preset(self) -> None:
        card = Card(self, "Preset")
        body = card.body()
        # "Custom" is a state, not a choice — showing it as a fifth button both
        # crowded the row and implied you could click your way into it.
        current = self.settings.matching_preset()
        self.preset_buttons = segmented(body, list(PRESETS),
                                        current if current != "Custom" else "",
                                        self._apply_preset)
        self.preset_buttons.grid(row=0, column=0, sticky="ew")
        self.preset_hint = ctk.CTkLabel(body, text="", font=t.font(11),
                                        text_color=t.MUTED, anchor="w")
        self.preset_hint.grid(row=1, column=0, sticky="w", pady=(t.SM, 0))
        self._add(card)
        self._refresh_preset_label()

    def _apply_preset(self, name: str) -> None:
        if name not in PRESETS:
            return
        self.settings.apply_preset(name)
        self._reload_controls()
        self._changed(refresh_preset=True)

    def _refresh_preset_label(self) -> None:
        name = self.settings.matching_preset()
        self.preset_buttons.set(name if name != "Custom" else "")
        self.preset_hint.configure(text=PRESET_HINTS.get(name, ""))

    # -- encoding -------------------------------------------------------
    def _build_encoding(self) -> None:
        card = Card(self, "Format & quality")
        body = card.body()

        formats = available_output_formats()
        if self.settings.output_format not in formats:
            self.settings.output_format = formats[0]
        self.format_buttons = segmented(body, [f.upper() for f in formats],
                                        self.settings.output_format.upper(),
                                        self._set_format)
        self.format_buttons.grid(row=0, column=0, sticky="ew")

        self.quality_row = SliderRow(
            body, "Quality", 1, 100, self.settings.quality, self._set_quality, "%",
            hint="Lower is smaller. 80–85 is visually lossless for most photos.")
        self.quality_row.grid(row=1, column=0, sticky="ew", pady=(t.MD, 0))

        self.lossless_switch = switch(body, "Lossless (ignores quality)",
                                      self.settings.lossless, self._set_lossless)
        self.lossless_switch.grid(row=2, column=0, sticky="w", pady=(t.MD, 0))

        self.effort_row = SliderRow(
            body, "Encoder effort", 0, 6, self.settings.effort, self._set_effort,
            hint="Higher squeezes a little more out of each file, and takes longer.")
        self.effort_row.grid(row=3, column=0, sticky="ew", pady=(t.MD, 0))

        threads = ctk.CTkFrame(body, fg_color="transparent")
        threads.grid(row=4, column=0, sticky="ew", pady=(t.MD, 0))
        threads.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(threads, text="Parallel workers", font=t.font(12),
                     text_color=t.TEXT, anchor="w").grid(row=0, column=0, sticky="w")
        current = "Auto" if self.settings.threads == 0 else str(self.settings.threads)
        self.threads_menu = option_menu(threads, THREAD_LABELS,
                                        current if current in THREAD_LABELS else "Auto",
                                        self._set_threads, width=110)
        self.threads_menu.grid(row=0, column=1, sticky="e")
        self._add(card)

    def _set_format(self, label: str) -> None:
        self.settings.output_format = label.lower()
        self._changed()

    def _set_quality(self, value: int) -> None:
        self.settings.quality = value
        self._changed()

    def _set_lossless(self, value: bool) -> None:
        self.settings.lossless = value
        self._changed()

    def _set_effort(self, value: int) -> None:
        self.settings.effort = value
        self._changed()

    def _set_threads(self, label: str) -> None:
        self.settings.threads = 0 if label == "Auto" else int(label)
        self._changed(refresh_preset=False)

    # -- geometry -------------------------------------------------------
    def _build_geometry(self) -> None:
        card = Card(self, "Size & shape")
        body = card.body()

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Downscale", font=t.font(12), text_color=t.TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.resize_menu = option_menu(row, list(RESIZE_LABELS.values()),
                                       RESIZE_LABELS[self.settings.resize_mode],
                                       self._set_resize_mode, width=170)
        self.resize_menu.grid(row=0, column=1, sticky="e")

        self.resize_value_row = ctk.CTkFrame(body, fg_color="transparent")
        self.resize_value_row.grid(row=1, column=0, sticky="ew", pady=(t.SM, 0))
        self.resize_value_row.grid_columnconfigure(0, weight=1)
        self.resize_value_caption = ctk.CTkLabel(self.resize_value_row, text="",
                                                 font=t.font(11), text_color=t.MUTED,
                                                 anchor="w")
        self.resize_value_caption.grid(row=0, column=0, sticky="w")
        self.resize_entry = ctk.CTkEntry(self.resize_value_row, width=100,
                                         font=t.font(12), fg_color=t.SURFACE_ALT,
                                         border_color=t.BORDER, text_color=t.TEXT,
                                         corner_radius=t.RADIUS_SM)
        self.resize_entry.grid(row=0, column=1, sticky="e")
        self.resize_entry.bind("<FocusOut>", lambda _e: self._commit_resize_value())
        self.resize_entry.bind("<Return>", lambda _e: self._commit_resize_value())

        ctk.CTkLabel(body, text="Never upscales — a limit above the original is ignored.",
                     font=t.font(10), text_color=t.FAINT, anchor="w").grid(
            row=2, column=0, sticky="w", pady=(t.XS, 0))

        section_label(body, "Square").grid(row=3, column=0, sticky="w", pady=(t.MD, t.XS))
        self.square_buttons = segmented(body, ["Off", "Crop", "Canvas"],
                                        self.settings.square_mode.capitalize()
                                        if self.settings.square_mode != "off" else "Off",
                                        self._set_square)
        self.square_buttons.grid(row=4, column=0, sticky="ew")

        self.fill_row = ctk.CTkFrame(body, fg_color="transparent")
        self.fill_row.grid(row=5, column=0, sticky="ew", pady=(t.SM, 0))
        self.fill_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.fill_row, text="Canvas fill", font=t.font(11),
                     text_color=t.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        self.fill_entry = ctk.CTkEntry(self.fill_row, width=120, font=t.font(12),
                                       fg_color=t.SURFACE_ALT, border_color=t.BORDER,
                                       text_color=t.TEXT, corner_radius=t.RADIUS_SM,
                                       placeholder_text="transparent or #ffffff")
        self.fill_entry.insert(0, self.settings.canvas_fill)
        self.fill_entry.grid(row=0, column=1, sticky="e")
        self.fill_entry.bind("<FocusOut>", lambda _e: self._commit_fill())
        self.fill_entry.bind("<Return>", lambda _e: self._commit_fill())
        self._add(card)

    def _set_resize_mode(self, label: str) -> None:
        self.settings.resize_mode = RESIZE_BY_LABEL[label]
        if self.settings.resize_mode == "megapixels" and self.settings.resize_value > 500:
            self.settings.resize_value = 12.0
        elif self.settings.resize_mode != "megapixels" and self.settings.resize_value < 16:
            self.settings.resize_value = 2048.0
        self._changed()
        self._reload_resize_entry()

    def _commit_resize_value(self) -> None:
        try:
            self.settings.resize_value = float(self.resize_entry.get().strip())
        except ValueError:
            pass  # keep the old value; _reload_resize_entry puts it back on screen
        self._changed()
        self._reload_resize_entry()

    def _reload_resize_entry(self) -> None:
        value = self.settings.resize_value
        text = f"{value:g}"
        self.resize_entry.delete(0, "end")
        self.resize_entry.insert(0, text)
        unit = "megapixels" if self.settings.resize_mode == "megapixels" else "pixels"
        self.resize_value_caption.configure(text=f"Limit ({unit})")

    def _set_square(self, label: str) -> None:
        self.settings.square_mode = label.lower()
        self._changed()

    def _commit_fill(self) -> None:
        self.settings.canvas_fill = self.fill_entry.get().strip() or "transparent"
        self._changed()
        self.fill_entry.delete(0, "end")
        self.fill_entry.insert(0, self.settings.canvas_fill)

    # -- metadata -------------------------------------------------------
    def _build_metadata(self) -> None:
        card = Card(self, "Metadata")
        body = card.body()
        self.metadata_switch = switch(body, "Keep EXIF and color profile",
                                      self.settings.keep_metadata, self._set_metadata)
        self.metadata_switch.grid(row=0, column=0, sticky="w")
        self.gps_switch = switch(body, "…but remove GPS location",
                                 self.settings.strip_gps, self._set_gps)
        self.gps_switch.grid(row=1, column=0, sticky="w", pady=(t.SM, 0))
        ctk.CTkLabel(body, text="With metadata off, colors are converted to sRGB so "
                               "untagged files still look right.",
                     font=t.font(10), text_color=t.FAINT, anchor="w",
                     wraplength=300, justify="left").grid(row=2, column=0, sticky="w",
                                                          pady=(t.SM, 0))
        self._add(card)

    def _set_metadata(self, value: bool) -> None:
        self.settings.keep_metadata = value
        self._changed()

    def _set_gps(self, value: bool) -> None:
        self.settings.strip_gps = value
        self._changed(refresh_preset=False)

    # -- destination ----------------------------------------------------
    def _build_destination(self) -> None:
        card = Card(self, "Where to save")
        body = card.body()

        self.dest_menu = option_menu(body, list(DEST_LABELS.values()),
                                     DEST_LABELS[self.settings.dest_mode],
                                     self._set_dest_mode, width=240)
        self.dest_menu.grid(row=0, column=0, sticky="ew")

        self.subfolder_row = ctk.CTkFrame(body, fg_color="transparent")
        self.subfolder_row.grid(row=1, column=0, sticky="ew", pady=(t.SM, 0))
        self.subfolder_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.subfolder_row, text="Folder name", font=t.font(11),
                     text_color=t.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        self.subfolder_entry = ctk.CTkEntry(self.subfolder_row, width=140,
                                            font=t.font(12), fg_color=t.SURFACE_ALT,
                                            border_color=t.BORDER, text_color=t.TEXT,
                                            corner_radius=t.RADIUS_SM)
        self.subfolder_entry.insert(0, self.settings.subfolder_name)
        self.subfolder_entry.grid(row=0, column=1, sticky="e")
        self.subfolder_entry.bind("<FocusOut>", lambda _e: self._commit_subfolder())
        self.subfolder_entry.bind("<Return>", lambda _e: self._commit_subfolder())

        self.custom_row = ctk.CTkFrame(body, fg_color="transparent")
        self.custom_row.grid(row=2, column=0, sticky="ew", pady=(t.SM, 0))
        self.custom_row.grid_columnconfigure(0, weight=1)
        self.custom_label = ctk.CTkLabel(self.custom_row, text="", font=t.font(11),
                                         text_color=t.MUTED, anchor="w")
        self.custom_label.grid(row=0, column=0, sticky="w")
        ghost_button(self.custom_row, "Browse…", self._pick_folder, height=30,
                     width=90).grid(row=0, column=1, sticky="e")

        section_label(body, "If a file already exists").grid(row=3, column=0, sticky="w",
                                                             pady=(t.MD, t.XS))
        self.existing_buttons = segmented(body, ["Skip", "Overwrite", "Rename"],
                                          self.settings.on_existing.capitalize(),
                                          self._set_existing)
        self.existing_buttons.grid(row=4, column=0, sticky="ew")
        self._add(card, pady=(0, t.SM))

    def _set_dest_mode(self, label: str) -> None:
        self.settings.dest_mode = DEST_BY_LABEL[label]
        if self.settings.dest_mode == "custom" and not self.settings.dest_folder:
            self._pick_folder()
        self._changed(refresh_preset=False)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose an output folder")
        if chosen:
            self.settings.dest_folder = chosen
            self.settings.dest_mode = "custom"
            self.dest_menu.set(DEST_LABELS["custom"])
        elif self.settings.dest_mode == "custom" and not self.settings.dest_folder:
            self.settings.dest_mode = "subfolder"  # cancelled with nothing set
            self.dest_menu.set(DEST_LABELS["subfolder"])
        self._changed(refresh_preset=False)

    def _commit_subfolder(self) -> None:
        self.settings.subfolder_name = self.subfolder_entry.get().strip() or "Converted"
        self._changed(refresh_preset=False)
        self.subfolder_entry.delete(0, "end")
        self.subfolder_entry.insert(0, self.settings.subfolder_name)

    def _set_existing(self, label: str) -> None:
        self.settings.on_existing = label.lower()
        self._changed(refresh_preset=False)

    # -- conditional visibility -----------------------------------------
    def _sync_conditional_rows(self) -> None:
        """Hide options that can't apply, instead of leaving dead controls on
        screen (v1 left the metadata toggle enabled while ignoring it)."""
        show = self.settings.resize_mode != "none"
        _toggle(self.resize_value_row, show, row=1)
        if show:
            self._reload_resize_entry()

        _toggle(self.fill_row, self.settings.square_mode == "canvas", row=5)
        _toggle(self.subfolder_row, self.settings.dest_mode == "subfolder", row=1)
        _toggle(self.custom_row, self.settings.dest_mode == "custom", row=2)
        if self.settings.dest_mode == "custom":
            folder = self.settings.dest_folder or "No folder chosen"
            self.custom_label.configure(text=_ellipsize(folder, 34))

        # Quality is meaningless in lossless mode, and GPS-stripping is
        # meaningless when no metadata is written at all.
        _set_enabled(self.quality_row.slider, not self.settings.lossless)
        _set_enabled(self.gps_switch, self.settings.keep_metadata)

        # Only WebP has a real lossless mode here. JPEG has none, and AVIF's
        # quality=100 is near-lossless — offering the toggle there would have
        # promised something the encoder does not deliver. PNG is always
        # lossless, so the switch would be noise.
        lossless_applies = self.settings.output_format == "webp"
        if self.settings.lossless and not lossless_applies:
            self.lossless_switch.variable.set(False)
            self.settings.lossless = False
        _set_enabled(self.lossless_switch, lossless_applies)

    def _reload_controls(self) -> None:
        """Push settings back into every widget (after a preset is applied)."""
        self._building = True
        self.preset_buttons.set(self.settings.matching_preset()
                                if self.settings.matching_preset() != "Custom" else "")
        self.format_buttons.set(self.settings.output_format.upper())
        self.quality_row.set(self.settings.quality)
        self.effort_row.set(self.settings.effort)
        self.lossless_switch.variable.set(self.settings.lossless)
        self.resize_menu.set(RESIZE_LABELS[self.settings.resize_mode])
        self.metadata_switch.variable.set(self.settings.keep_metadata)
        self.gps_switch.variable.set(self.settings.strip_gps)
        self.square_buttons.set(self.settings.square_mode.capitalize()
                                if self.settings.square_mode != "off" else "Off")
        self._building = False
        self._reload_resize_entry()


def _toggle(widget, visible: bool, row: int) -> None:
    if visible:
        widget.grid(row=row, column=0, sticky="ew", pady=(t.SM, 0))
    else:
        widget.grid_remove()


def _set_enabled(widget, enabled: bool) -> None:
    widget.configure(state="normal" if enabled else "disabled")


def _ellipsize(text: str, limit: int) -> str:
    return text if len(text) <= limit else "…" + text[-(limit - 1):]
