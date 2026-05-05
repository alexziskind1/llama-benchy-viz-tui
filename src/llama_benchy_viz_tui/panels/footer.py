"""Footer panel: schema + producer version + live status + quit hint."""

from __future__ import annotations

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from ..state import Snapshot
from ._common import ACCENT, DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    return True


def render(snap: Snapshot) -> RenderableType:
    line = Text()
    line.append("schema: ", style=DIM)
    line.append("llama-benchy-progress.v1", style="white")
    line.append("    producer: ", style=DIM)
    line.append(snap.llama_benchy_version or "unknown", style="white")
    line.append("    status: ", style=DIM)
    line.append(
        "FROZEN" if snap.finished else "LIVE",
        style="yellow" if snap.finished else ACCENT,
    )
    line.append("    quit: ", style=DIM)
    line.append("Ctrl+C", style="white")
    return Panel(line, border_style=PANEL_BORDER, padding=(0, 1))
