"""Summary panel: Leader Now / Best Avg / Fastest TTFT cards."""

from __future__ import annotations

from typing import Callable, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..domain import Snapshot, SlotState
from ._common import ACCENT, DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    return True


def render(snap: Snapshot) -> RenderableType:
    leader = snap.leader_now()
    best = snap.best_avg()
    fastest = snap.fastest_ttft()

    leader_card = _summary_card(
        "LEADER NOW", "🏆", "#ffb000", leader,
        lambda s: f"{s.current_tps:.1f} tok/s",
    )
    best_card = _summary_card(
        "BEST AVG", "★", "#a96bff", best,
        lambda s: f"{s.avg_tps:.1f} tok/s",
    )
    fast_card = _summary_card(
        "FASTEST TTFT", "⚡", ACCENT, fastest,
        lambda s: f"{s.last_ttft_s:.2f} s" if s.last_ttft_s is not None else "—",
    )

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(leader_card, best_card, fast_card)
    return table


def _summary_card(
    title: str,
    icon: str,
    icon_color: str,
    pick: Optional[SlotState],
    bottom_fmt: Callable[[SlotState], str],
) -> Panel:
    head = Text()
    head.append(f"{icon} ", style=icon_color)
    head.append(title, style=DIM)
    if pick is None:
        body = Text("—", style=DIM)
        sub = Text("—", style=DIM)
    else:
        body = Text(pick.label, style=f"bold {pick.color}")
        sub = Text(bottom_fmt(pick), style="bold white")
    return Panel(Group(head, body, sub), border_style=PANEL_BORDER, padding=(0, 1))
