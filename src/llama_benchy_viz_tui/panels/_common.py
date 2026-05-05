"""Shared visual constants + tiny helpers used by every panel."""

from __future__ import annotations

from rich.text import Text

ACCENT = "#39ff7a"
PANEL_BORDER = "grey30"
DIM = "grey50"


def fmt_elapsed(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def phase_badge(phase: str, color: str) -> Text:
    style_map = {
        "LOADING": ("LOADING", "black on grey50"),
        "PREFILL": ("PREFILL", f"black on {ACCENT}"),
        "DECODE": ("DECODE", f"black on {color}"),
        "DONE": ("DONE", "black on grey70"),
        "ERROR": ("ERROR", "white on red"),
    }
    label, style = style_map.get(phase, (phase, "white"))
    return Text(f" {label} ", style=style)
