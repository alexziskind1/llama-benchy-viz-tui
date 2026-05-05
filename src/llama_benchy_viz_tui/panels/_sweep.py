"""Shared rendering for the four sweep panels (pp / tg / depth / concurrency).

Each axis-specific panel module is a thin wrapper that picks the axis it
cares about and calls `render_sweep` here. Activation is "any slot has
multiple distinct values along this axis" — i.e. a sweep was actually
performed within the run.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..state import CellAggregate, CellKey, Snapshot, SlotState
from ._common import DIM, PANEL_BORDER


def any_slot_varies(snap: Snapshot, attr: str) -> bool:
    return any(getattr(s, attr) for s in snap.slots)


def render_sweep(
    snap: Snapshot,
    *,
    title: str,
    axis_label: str,
    axis_extractor: Callable[[CellKey], int],
    varies_attr: str,
) -> RenderableType:
    """Render a sweep panel.

    `axis_extractor(cell_key) -> int` picks which dimension the panel groups by.
    `varies_attr` is the SlotState boolean property used to skip slots that
    didn't sweep this axis (e.g. `'pp_varies'`).
    """
    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text(title, style="bold white"),
        Text(axis_label, style=DIM),
    )

    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=2)              # color dot
    body.add_column(ratio=2)              # slot label
    body.add_column(width=8, justify="right")     # axis value
    body.add_column(width=10, justify="right")    # pp tok/s
    body.add_column(width=10, justify="right")    # tg tok/s
    body.add_column(width=10, justify="right")    # peak tg
    body.add_column(width=10, justify="right")    # ttfr (ms)
    body.add_column(width=10, justify="right")    # est_ppt (ms)
    body.add_column(width=10, justify="right")    # e2e_ttft (ms)
    body.add_column(width=6, justify="right")     # progress

    body.add_row(
        Text(""),
        Text("stream", style=DIM),
        Text(axis_label, style=DIM),
        Text("pp tok/s", style=DIM),
        Text("tg tok/s", style=DIM),
        Text("peak tg", style=DIM),
        Text("ttfr (ms)", style=DIM),
        Text("est_ppt", style=DIM),
        Text("e2e_ttft", style=DIM),
        Text("runs", style=DIM),
    )

    rendered_any = False
    for slot in snap.slots:
        if not getattr(slot, varies_attr):
            continue
        # Group cells by the axis value, aggregating across the other axes.
        groups: Dict[int, List[CellAggregate]] = {}
        for ck, cell in slot.cells.items():
            groups.setdefault(axis_extractor(ck), []).append(cell)
        for axis_val in sorted(groups):
            cells = groups[axis_val]
            pp_means = [c.pp_tps_mean for c in cells if c.pp_tps_mean is not None]
            tg_means = [c.tg_tps_mean for c in cells if c.tg_tps_mean is not None]
            peak_means = [c.peak_tg_mean for c in cells if c.peak_tg_mean is not None]
            ttft_means = [c.ttft_s_mean for c in cells if c.ttft_s_mean is not None]
            ttfr_means = [c.ttfr_s_mean for c in cells if c.ttfr_s_mean is not None]
            est_means = [c.est_ppt_s_mean for c in cells if c.est_ppt_s_mean is not None]
            done = sum(c.completed for c in cells)
            in_flight = sum(c.in_flight for c in cells)
            pp_str = f"{(sum(pp_means) / len(pp_means)):>7.0f}" if pp_means else "    —  "
            tg_str = f"{(sum(tg_means) / len(tg_means)):>6.1f}" if tg_means else "   —  "
            peak_str = (
                f"{(sum(peak_means) / len(peak_means)):>6.1f}"
                if peak_means
                else "   —  "
            )
            ttfr_str = _ms(ttfr_means) if ttfr_means else _ms(ttft_means)
            est_str = _ms(est_means) if est_means else _ms(ttft_means)
            e2e_str = _ms(ttft_means)
            status = f"{done}{'  …' if in_flight else ''}"
            body.add_row(
                Text("●", style=slot.color),
                Text(slot.label, style="white"),
                Text(f"{axis_val:,}", style=slot.color),
                Text(pp_str, style="white"),
                Text(tg_str, style="white"),
                Text(peak_str, style="white"),
                Text(ttfr_str, style="white"),
                Text(est_str, style="white"),
                Text(e2e_str, style="white"),
                Text(status, style="white"),
            )
            rendered_any = True

    if not rendered_any:
        body.add_row(
            Text(""),
            Text("waiting…", style=DIM),
            Text(""), Text(""), Text(""), Text(""),
            Text(""), Text(""), Text(""), Text(""),
        )

    return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))


def _ms(values: List[float]) -> str:
    """Format a list of seconds-valued samples as right-justified ms mean."""
    if not values:
        return "    —  "
    return f"{(sum(values) / len(values)) * 1000:>7.1f}"
