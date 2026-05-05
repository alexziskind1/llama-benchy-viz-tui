"""Sweep panel for `--depth` (context size)."""

from __future__ import annotations

from rich.console import RenderableType

from ..state import Snapshot
from ._sweep import any_slot_varies, render_sweep


def is_active(snap: Snapshot) -> bool:
    return any_slot_varies(snap, "depth_varies")


def render(snap: Snapshot) -> RenderableType:
    return render_sweep(
        snap,
        title="DEPTH SWEEP",
        axis_label="depth",
        axis_extractor=lambda ck: ck.depth,
        varies_attr="depth_varies",
    )
