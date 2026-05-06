"""Thin façade: domain Snapshot → ViewModel → TUI Rich layout.

This file used to contain panel rendering. Those moved to
``renderer/tui/modules.py`` (renderer adapters) and the layout to
``renderer/tui/layout.py``. The ``view/`` layer in between handles the
ModuleSpec/LayoutSpec composition.

Kept as a small entry point so callers (``__main__.py``, tests, ad-hoc
notebook scripts) can keep doing ``from .ui import render`` and get a
ready-to-print Rich renderable.
"""

from __future__ import annotations

from typing import Optional

from rich.console import RenderableType

from .domain import Snapshot
from .renderer.tui import render_view_model
from .view import DashboardMode, build_view_model, detect


def render(
    snap: Snapshot,
    *,
    console_width: int,
    console_height: int,
    mode: Optional[DashboardMode] = None,
) -> RenderableType:
    """Compose and render one frame.

    ``mode`` overrides auto-detection when supplied (used for
    ``--mode`` on the CLI). Otherwise the dashboard adapts to the
    current snapshot — single vs. race based on slot count, live vs.
    static based on ``snap.finished``.
    """
    chosen_mode = mode if mode is not None else detect(snap)
    view = build_view_model(snap, chosen_mode)
    return render_view_model(
        view,
        console_width=console_width,
        console_height=console_height,
    )
