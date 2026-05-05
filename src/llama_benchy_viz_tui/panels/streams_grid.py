"""Streams grid panel: 2×2 cards, one per slot."""

from __future__ import annotations

from typing import List

from rich.align import Align
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..chart import render_sparkline
from ..domain import SlotState, Snapshot
from ._common import DIM, PANEL_BORDER, phase_badge


def is_active(snap: Snapshot) -> bool:
    return True


def render(snap: Snapshot) -> RenderableType:
    cards: List[RenderableType] = []
    for slot in range(4):
        match = next((s for s in snap.slots if s.slot == slot), None)
        if match is None:
            cards.append(
                Panel(
                    Align.center(Text("(no stream)", style=DIM), vertical="middle"),
                    border_style=PANEL_BORDER,
                    padding=(0, 1),
                )
            )
        else:
            cards.append(_stream_card(match))

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(cards[0], cards[1])
    grid.add_row(cards[2], cards[3])
    return grid


def _stream_card(slot: SlotState) -> Panel:
    color = slot.color

    head = Table.grid(expand=True, padding=(0, 1))
    head.add_column(width=3)
    head.add_column(ratio=1)
    slot_badge = Text(f" {slot.slot + 1} ", style=f"black on {color}")
    label = Text(slot.label or f"slot {slot.slot + 1}", style="bold white")
    head.add_row(slot_badge, label)

    phase_row = Table.grid(expand=True, padding=(0, 1))
    phase_row.add_column()
    phase_row.add_column(ratio=1, justify="right")
    phase_row.add_row(
        phase_badge(slot.phase, color),
        render_sparkline(list(slot.sparkline), color, width=18),
    )

    big = Text()
    big.append(f"{slot.current_tps:5.1f}", style=f"bold {color}")
    big.append(" tok/s", style="white")

    metrics = Table.grid(expand=True, padding=(0, 1))
    metrics.add_column(ratio=1)
    metrics.add_column(ratio=1)
    metrics.add_column(ratio=1)
    metrics.add_row(
        Text.assemble(("AVG ", DIM), (f"{slot.avg_tps:>6.1f} t/s", "white")),
        Text.assemble(
            ("TTFT ", DIM),
            (
                f"{slot.last_ttft_s:>5.2f} s"
                if slot.last_ttft_s is not None
                else "  N/A  ",
                "white",
            ),
        ),
        Text.assemble(
            ("PP ", DIM),
            (
                f"{slot.last_pp_tps:>5.0f} t/s"
                if slot.last_pp_tps is not None
                else "  N/A    ",
                "white",
            ),
        ),
    )
    metrics.add_row(
        Text.assemble(("GEN ", DIM), (f"{slot.total_gen_tokens:>8,d}", "white")),
        Text.assemble(("PROMPT ", DIM), (f"{slot.last_prompt_tokens:>6,d}", "white")),
        Text.assemble(("CONC ", DIM), (f"{slot.concurrency or 1:>4d}", "white")),
    )

    snippet = Text()
    snippet.append("OUTPUT > ", style=DIM)
    text = (slot.output_snippet or "…")[-180:].replace("\n", " ")
    snippet.append(text, style="grey70")

    body = Group(head, phase_row, big, metrics, snippet)
    return Panel(body, border_style=color, padding=(0, 1))
