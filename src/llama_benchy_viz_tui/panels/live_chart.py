"""Hero tok/s chart — Braille line per slot, last `CHART_HISTORY_S` seconds."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..chart import render_chart
from ..domain import CHART_HISTORY_S, Snapshot
from ._common import DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    return True


def render(snap: Snapshot, *, width: int = 100, height: int = 12) -> RenderableType:
    series = []
    for s in snap.slots:
        series.append((s.label or f"slot {s.slot + 1}", s.color, list(s.history)))

    title = Table.grid(expand=True)
    title.add_column(ratio=1)
    title.add_column(justify="right")
    title.add_row(
        Text("LIVE PERFORMANCE", style="bold white"),
        Text("tok/s", style=DIM),
    )

    now = snap.last_event_ts or 0.0
    chart_text = render_chart(
        series,
        width=width,
        height=max(8, height),
        history_seconds=CHART_HISTORY_S,
        now=now,
        y_max=snap.chart_y_max,
    )

    return Panel(Group(title, chart_text), border_style=PANEL_BORDER, padding=(0, 1))
