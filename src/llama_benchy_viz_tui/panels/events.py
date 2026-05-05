"""Events panel: rolling event log."""

from __future__ import annotations

from datetime import datetime

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..state import Snapshot
from ._common import DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    # Off by default — the events log is mostly useful for debugging
    # multi-target / multi-cell / failing runs. Enable with --show-events.
    return snap.show_events


def render(snap: Snapshot) -> RenderableType:
    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text("EVENTS", style="bold white"),
        Text("(Live)", style=DIM),
    )

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=10)
    table.add_column()

    rows = list(snap.events)[-7:]
    if not rows:
        table.add_row(Text("—", style=DIM), Text("waiting…", style=DIM))
    else:
        for ev in rows:
            ts = datetime.fromtimestamp(ev.ts).strftime("%H:%M:%S")
            color = "white"
            if ev.slot is not None:
                slot = next((s for s in snap.slots if s.slot == ev.slot), None)
                if slot is not None:
                    color = slot.color
            line = Text()
            line.append("● ", style=color)
            line.append(f"{ev.label} ", style=color)
            line.append(ev.text, style="white")
            table.add_row(Text(ts, style=DIM), line)
    foot = Text("Showing latest events…", style=DIM)
    return Panel(Group(head, table, foot), border_style=PANEL_BORDER, padding=(0, 1))
