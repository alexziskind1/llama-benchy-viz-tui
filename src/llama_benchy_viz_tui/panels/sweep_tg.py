"""Sweep panel for `--tg` (token generation counts)."""

from __future__ import annotations

from rich.console import RenderableType

from ..domain import Snapshot
from ._sweep import any_slot_varies, render_sweep


def is_active(snap: Snapshot) -> bool:
    return any_slot_varies(snap, "tg_varies")


def render(snap: Snapshot) -> RenderableType:
    return render_sweep(
        snap,
        title="TG SWEEP",
        axis_label="tg",
        axis_extractor=lambda ck: ck.tg,
        varies_attr="tg_varies",
    )
