"""Sweep panel for `--pp` (prompt processing token counts)."""

from __future__ import annotations

from rich.console import RenderableType

from ..domain import Snapshot
from ._sweep import any_slot_varies, render_sweep


def is_active(snap: Snapshot) -> bool:
    return any_slot_varies(snap, "pp_varies")


def render(snap: Snapshot) -> RenderableType:
    return render_sweep(
        snap,
        title="PP SWEEP",
        axis_label="pp",
        axis_extractor=lambda ck: ck.pp,
        varies_attr="pp_varies",
    )
