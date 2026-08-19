"""Design tokens.

Every color is a (light, dark) pair — CustomTkinter resolves the right one per
appearance mode, so nothing has to be re-styled when the theme flips. v1
hardcoded "gray90"/"gray17" in fourteen places; this is that, once.
"""

from __future__ import annotations

import customtkinter as ctk

# --- surfaces --------------------------------------------------------------
BG = ("#f2f3f6", "#131418")
SURFACE = ("#ffffff", "#1b1d23")
SURFACE_ALT = ("#e9ebf0", "#22252c")
BORDER = ("#dcdfe6", "#2b2e37")
BORDER_STRONG = ("#c3c8d2", "#3a3e49")

# --- text ------------------------------------------------------------------
TEXT = ("#15171c", "#f1f2f5")
MUTED = ("#6a7180", "#888f9c")
FAINT = ("#9aa1ad", "#666c78")

# --- intent ----------------------------------------------------------------
ACCENT = ("#2563eb", "#3b82f6")
ACCENT_HOVER = ("#1d4ed8", "#2f74e6")
ACCENT_SOFT = ("#e5edff", "#1d2a44")
SUCCESS = ("#15803d", "#4ade80")
WARNING = ("#b45309", "#fbbf24")
DANGER = ("#b91c1c", "#f87171")
DANGER_HOVER = ("#991b1b", "#dc2626")

# --- spacing scale ---------------------------------------------------------
XS, SM, MD, LG, XL = 4, 8, 14, 20, 28

RADIUS = 14
RADIUS_SM = 9


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


# Tk has no generic "monospace" alias — asking for it silently hands back
# Arial, which is why the log columns never lined up. Name real families and
# check them against what this machine has.
_MONO_CANDIDATES = ("Menlo", "SF Mono", "Monaco",          # macOS
                    "Cascadia Mono", "Consolas",           # Windows
                    "DejaVu Sans Mono", "Liberation Mono", # Linux
                    "Courier New", "Courier")
_mono_family: str | None = None


def mono_font(size: int = 11) -> ctk.CTkFont:
    global _mono_family
    if _mono_family is None:
        import tkinter.font as tkfont

        available = {name.lower() for name in tkfont.families()}
        _mono_family = next((f for f in _MONO_CANDIDATES if f.lower() in available),
                            "Courier")
    return ctk.CTkFont(family=_mono_family, size=size)


def resolve(color: tuple[str, str] | str) -> str:
    """Flatten a token to one hex string, for raw Tk widgets (Canvas) that
    don't understand CustomTkinter's tuple colors."""
    if isinstance(color, str):
        return color
    return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]


def apply_appearance(theme: str) -> None:
    ctk.set_appearance_mode({"light": "Light", "dark": "Dark"}.get(theme, "System"))
