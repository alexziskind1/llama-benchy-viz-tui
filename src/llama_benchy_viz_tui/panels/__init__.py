"""Modular panel package.

Each panel module exports two functions:

    is_active(snap: Snapshot) -> bool   # should this panel be shown right now?
    render(snap: Snapshot) -> Renderable  # the panel's renderable

The composer in ``ui.py`` imports panels and asks each whether to include
it in the current frame. Always-on panels (header, summary, etc.) just
return ``True`` from ``is_active``; conditional panels (sweep_pp,
sweep_tg, …) only return ``True`` once their data exists.
"""

from . import (
    cells,
    events,
    footer,
    header,
    live_chart,
    ranking,
    streams_grid,
    summary,
)

__all__ = [
    "cells",
    "events",
    "footer",
    "header",
    "live_chart",
    "ranking",
    "streams_grid",
    "summary",
]
