"""Reusable pieces. Built once here so screens stay layout-only."""

from __future__ import annotations

import math
from typing import Callable

import customtkinter as ctk

from gui import theme as t


class Card(ctk.CTkFrame):
    """A titled surface panel. The base unit of every screen."""

    def __init__(self, parent, title: str | None = None, subtitle: str | None = None, **kwargs):
        kwargs.setdefault("fg_color", t.SURFACE)
        kwargs.setdefault("corner_radius", t.RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", t.BORDER)
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._row = 0

        if title:
            head = ctk.CTkFrame(self, fg_color="transparent")
            head.grid(row=0, column=0, sticky="ew", padx=t.MD, pady=(t.MD, t.XS))
            head.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(head, text=title, font=t.font(13, "bold"), text_color=t.TEXT,
                         anchor="w").grid(row=0, column=0, sticky="w")
            if subtitle:
                ctk.CTkLabel(head, text=subtitle, font=t.font(11), text_color=t.MUTED,
                             anchor="e").grid(row=0, column=1, sticky="e")
            self._row = 1

    def body(self) -> ctk.CTkFrame:
        """Padded container for the card's content."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=self._row, column=0, sticky="nsew",
                   padx=t.MD, pady=(t.SM if self._row else t.MD, t.MD))
        frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(self._row, weight=1)
        self._row += 1
        return frame


def section_label(parent, text: str) -> ctk.CTkLabel:
    label = ctk.CTkLabel(parent, text=text.upper(), font=t.font(10, "bold"),
                         text_color=t.FAINT, anchor="w")
    return label


class StatTile(ctk.CTkFrame):
    """Big number + caption. Used across progress and results."""

    def __init__(self, parent, caption: str, value: str = "—",
                 color: tuple[str, str] = t.TEXT, value_size: int = 24):
        super().__init__(parent, fg_color=t.SURFACE_ALT, corner_radius=t.RADIUS_SM)
        self.grid_columnconfigure(0, weight=1)
        self.value_label = ctk.CTkLabel(self, text=value, font=t.font(value_size, "bold"),
                                        text_color=color)
        self.value_label.grid(row=0, column=0, pady=(t.MD, 0), padx=t.MD)
        ctk.CTkLabel(self, text=caption, font=t.font(11), text_color=t.MUTED).grid(
            row=1, column=0, pady=(2, t.MD), padx=t.MD)

    def set(self, value: str) -> None:
        self.value_label.configure(text=value)


class ProgressRing(ctk.CTkFrame):
    """Canvas-drawn progress ring with a percentage in the middle.

    A CTkProgressBar can't show a value inside itself, and this is the one
    element the user stares at for the whole run.
    """

    def __init__(self, parent, size: int = 168, thickness: int = 12):
        super().__init__(parent, fg_color="transparent")
        self.size, self.thickness = size, thickness
        self._fraction = 0.0
        self.canvas = ctk.CTkCanvas(self, width=size, height=size,
                                    highlightthickness=0, bd=0)
        self.canvas.pack()

        self.percent = ctk.CTkLabel(self, text="0%", font=t.font(34, "bold"),
                                    text_color=t.TEXT, fg_color="transparent")
        self.percent.place(relx=0.5, rely=0.44, anchor="center")
        self.caption = ctk.CTkLabel(self, text="", font=t.font(11), text_color=t.MUTED,
                                    fg_color="transparent")
        self.caption.place(relx=0.5, rely=0.63, anchor="center")
        self.redraw()

    def set(self, fraction: float, caption: str = "") -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        self.percent.configure(text=f"{round(self._fraction * 100)}%")
        if caption:
            self.caption.configure(text=caption)
        self.redraw()

    def redraw(self) -> None:
        pad = self.thickness / 2 + 2
        box = (pad, pad, self.size - pad, self.size - pad)
        self.canvas.configure(bg=t.resolve(t.SURFACE))
        self.canvas.delete("all")
        self.canvas.create_oval(*box, outline=t.resolve(t.SURFACE_ALT),
                                width=self.thickness)
        if self._fraction > 0:
            # -90° start, negative extent => clockwise from 12 o'clock.
            self.canvas.create_arc(*box, start=90, extent=-359.9 * self._fraction,
                                   style="arc", outline=t.resolve(t.ACCENT),
                                   width=self.thickness)


class SliderRow(ctk.CTkFrame):
    """Label + live value + slider, kept in sync as one unit."""

    def __init__(self, parent, label: str, from_: int, to: int, value: int,
                 on_change: Callable[[int], None], suffix: str = "", hint: str = ""):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._on_change = on_change
        self._suffix = suffix

        ctk.CTkLabel(self, text=label, font=t.font(12), text_color=t.TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.value_label = ctk.CTkLabel(self, text=f"{value}{suffix}",
                                        font=t.font(12, "bold"), text_color=t.ACCENT)
        self.value_label.grid(row=0, column=1, sticky="e")

        self.slider = ctk.CTkSlider(self, from_=from_, to=to, number_of_steps=to - from_,
                                    command=self._changed, button_color=t.ACCENT,
                                    button_hover_color=t.ACCENT_HOVER,
                                    progress_color=t.ACCENT, fg_color=t.SURFACE_ALT)
        self.slider.set(value)
        self.slider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(t.XS, 0))

        if hint:
            # wraplength, or a two-line hint silently loses its second half
            ctk.CTkLabel(self, text=hint, font=t.font(10), text_color=t.FAINT,
                         anchor="w", justify="left", wraplength=300).grid(
                row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _changed(self, raw: float) -> None:
        value = int(round(raw))
        self.value_label.configure(text=f"{value}{self._suffix}")
        self._on_change(value)

    def set(self, value: int) -> None:
        self.slider.set(value)
        self.value_label.configure(text=f"{value}{self._suffix}")


def segmented(parent, values: list[str], value: str,
              on_change: Callable[[str], None]) -> ctk.CTkSegmentedButton:
    widget = ctk.CTkSegmentedButton(
        parent, values=values, command=on_change, font=t.font(12),
        selected_color=t.ACCENT, selected_hover_color=t.ACCENT_HOVER,
        unselected_color=t.SURFACE_ALT, unselected_hover_color=t.BORDER,
        text_color=t.TEXT, corner_radius=t.RADIUS_SM,
    )
    widget.set(value)
    return widget


def option_menu(parent, values: list[str], value: str,
                on_change: Callable[[str], None], width: int = 150) -> ctk.CTkOptionMenu:
    widget = ctk.CTkOptionMenu(
        parent, values=values, command=on_change, width=width, font=t.font(12),
        fg_color=t.SURFACE_ALT, button_color=t.SURFACE_ALT,
        button_hover_color=t.BORDER_STRONG, text_color=t.TEXT,
        dropdown_fg_color=t.SURFACE, dropdown_text_color=t.TEXT,
        dropdown_hover_color=t.ACCENT_SOFT, corner_radius=t.RADIUS_SM,
    )
    widget.set(value)
    return widget


def primary_button(parent, text: str, command: Callable[[], None],
                   height: int = 44) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, height=height,
                         font=t.font(14, "bold"), corner_radius=t.RADIUS_SM,
                         fg_color=t.ACCENT, hover_color=t.ACCENT_HOVER,
                         text_color="#ffffff")


def ghost_button(parent, text: str, command: Callable[[], None],
                 height: int = 36, width: int = 0) -> ctk.CTkButton:
    kwargs = {"width": width} if width else {}
    return ctk.CTkButton(parent, text=text, command=command, height=height,
                         font=t.font(12), corner_radius=t.RADIUS_SM,
                         fg_color=t.SURFACE_ALT, hover_color=t.BORDER_STRONG,
                         text_color=t.TEXT, border_width=1, border_color=t.BORDER,
                         **kwargs)


def switch(parent, text: str, value: bool, on_change: Callable[[bool], None]) -> ctk.CTkSwitch:
    var = ctk.BooleanVar(value=value)
    widget = ctk.CTkSwitch(parent, text=text, variable=var, font=t.font(12),
                           text_color=t.TEXT, progress_color=t.ACCENT,
                           button_color="#ffffff", fg_color=t.BORDER_STRONG,
                           command=lambda: on_change(var.get()))
    widget.variable = var  # keep a reference so callers can flip it back
    return widget


class LogView(ctk.CTkTextbox):
    """Append-only log with a hard line cap.

    v1 created one Label per file — 5000 images meant 5000 live widgets and a
    frozen window. One textbox, trimmed from the top, stays flat.
    """

    MAX_LINES = 400

    def __init__(self, parent, height: int = 120):
        super().__init__(parent, height=height, font=t.mono_font(11),
                         fg_color=t.SURFACE_ALT, text_color=t.MUTED,
                         corner_radius=t.RADIUS_SM, border_width=0, wrap="none",
                         activate_scrollbars=True)
        self.configure(state="disabled")
        self._lines = 0

    def append(self, line: str) -> None:
        self.configure(state="normal")
        self.insert("end", line + "\n")
        self._lines += 1
        if self._lines > self.MAX_LINES:
            self.delete("1.0", f"{self._lines - self.MAX_LINES + 1}.0")
            self._lines = self.MAX_LINES
        self.see("end")
        self.configure(state="disabled")

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
        self._lines = 0


def relayout_ring_colors(widget) -> None:
    """Walk a widget tree and redraw any rings after an appearance change."""
    if isinstance(widget, ProgressRing):
        widget.redraw()
    for child in widget.winfo_children():
        relayout_ring_colors(child)
