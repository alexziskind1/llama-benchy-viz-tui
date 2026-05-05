"""Sweep panel for `--concurrency`."""

from __future__ import annotations

from rich.console import RenderableType

from ..domain import Snapshot
from ._sweep import any_slot_varies, render_sweep


def is_active(snap: Snapshot) -> bool:
    return any_slot_varies(snap, "concurrency_varies")


def render(snap: Snapshot) -> RenderableType:
    return render_sweep(
        snap,
        title="CONCURRENCY SWEEP",
        axis_label="conc",
        axis_extractor=lambda ck: ck.concurrency,
        varies_attr="concurrency_varies",
    )
