"""Ranking panel: slots sorted by avg tok/s."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..state import Snapshot
from ._common import DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    # Ranking is only meaningful when there's more than one stream to rank.
    return len(snap.slots) > 1


def render(snap: Snapshot) -> RenderableType:
    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text("LIVE RANKING", style="bold white"),
        Text("(by avg tok/s)", style=DIM),
    )

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=4)
    table.add_column(ratio=1)
    table.add_column(justify="right", width=14)

    rows = snap.ranking_by_avg()
    if not rows:
        table.add_row(Text("—", style=DIM), Text("waiting…", style=DIM), Text(""))
    else:
        for i, s in enumerate(rows[:6], start=1):
            table.add_row(
                Text(f"#{i}", style="bold white"),
                Text(s.label, style=s.color),
                Text(f"{s.avg_tps:.1f} tok/s", style="white"),
            )
    foot = Text("Higher avg tok/s is better", style=DIM)
    return Panel(Group(head, table, foot), border_style=PANEL_BORDER, padding=(0, 1))
