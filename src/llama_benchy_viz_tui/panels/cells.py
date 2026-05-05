"""Per-cell results panel.

One row per `(pp, tg, depth, concurrency)` cell. PP and TG throughput are
measured per-request and naturally pair within a cell, so a single results
table is more honest than splitting them across per-axis sweep panels.

When the cell count exceeds the visible rows, the panel becomes
scrollable (controlled by `state.cells_scroll_offset`) and renders a
vertical scrollbar (█/░ thumb) on the right edge.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..state import CellAggregate, CellKey, Snapshot, SlotState
from ._common import DIM, PANEL_BORDER


def is_active(snap: Snapshot) -> bool:
    return any(s.cells for s in snap.slots)


def min_height(snap: Snapshot) -> int:
    """Rows wanted to fit every cell.

    Panel border (2) + title row (1) + table-header row (1) + N data rows.
    For 1 cell that's 5 rows; for 42 cells, 46. The composer caps this to
    whatever the terminal can actually spare.
    """
    n_cells = sum(len(s.cells) for s in snap.slots)
    return max(5, n_cells + 4)


def render(
    snap: Snapshot,
    *,
    max_data_rows: Optional[int] = None,
) -> RenderableType:
    flat = _flat_cell_list(snap)
    n_cells = len(flat)

    visible_rows = max_data_rows if max_data_rows is not None else n_cells
    visible_rows = max(1, min(visible_rows, n_cells)) if n_cells else visible_rows
    scrollable = n_cells > visible_rows

    if scrollable:
        max_offset = n_cells - visible_rows
        offset = max(0, min(snap.cells_scroll_offset, max_offset))
        slice_lo = offset
        slice_hi = offset + visible_rows
    else:
        offset = 0
        slice_lo = 0
        slice_hi = n_cells

    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    if scrollable:
        right = Text(
            f"showing {slice_lo + 1}-{slice_hi} of {n_cells}   "
            "↑/↓ scroll  PgUp/PgDn page  g/G top/bottom",
            style="yellow",
        )
    else:
        right = Text("(per-cell results)", style=DIM)
    head.add_row(
        Text("BENCHMARK CELLS", style="bold white"),
        right,
    )

    body = _build_body_table(scrollable)

    # Header row.
    header_cells = [
        Text(""),
        Text("stream", style=DIM),
        Text("pp", style=DIM),
        Text("tg", style=DIM),
        Text("depth", style=DIM),
        Text("conc", style=DIM),
        Text("pp tok/s", style=DIM),
        Text("tg tok/s", style=DIM),
        Text("peak tg", style=DIM),
        Text("ttfr (ms)", style=DIM),
        Text("est_ppt", style=DIM),
        Text("e2e_ttft", style=DIM),
        Text("runs", style=DIM),
    ]
    if scrollable:
        header_cells.append(Text(" "))  # scrollbar column header is blank
    body.add_row(*header_cells)

    if not flat:
        empty_row = [Text("")] * (13 + (1 if scrollable else 0))
        empty_row[1] = Text("waiting…", style=DIM)
        body.add_row(*empty_row)
        return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))

    # Compute scrollbar geometry once for the visible window.
    if scrollable:
        thumb_size, thumb_start = _scrollbar_geometry(
            visible_rows=visible_rows, total_rows=n_cells, offset=offset
        )

    for i, (slot, ck, cell) in enumerate(flat[slice_lo:slice_hi]):
        cells_row = _format_cell_row(slot, ck, cell)
        if scrollable:
            in_thumb = thumb_start <= i < thumb_start + thumb_size
            scrollbar = Text("█", style="grey50") if in_thumb else Text("░", style="grey23")
            cells_row.append(scrollbar)
        body.add_row(*cells_row)

    return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))


def _flat_cell_list(
    snap: Snapshot,
) -> List[Tuple[SlotState, CellKey, CellAggregate]]:
    flat: List[Tuple[SlotState, CellKey, CellAggregate]] = []
    for slot in snap.slots:
        for ck in sorted(
            slot.cells.keys(),
            key=lambda k: (k.pp, k.tg, k.depth, k.concurrency),
        ):
            flat.append((slot, ck, slot.cells[ck]))
    return flat


def _build_body_table(scrollable: bool) -> Table:
    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=2)              # color dot
    body.add_column(ratio=2)              # stream label
    body.add_column(width=7, justify="right")     # pp
    body.add_column(width=7, justify="right")     # tg
    body.add_column(width=7, justify="right")     # depth
    body.add_column(width=5, justify="right")     # conc
    body.add_column(width=10, justify="right")    # pp tok/s
    body.add_column(width=10, justify="right")    # tg tok/s
    body.add_column(width=9, justify="right")     # peak tg
    body.add_column(width=10, justify="right")    # ttfr (ms)
    body.add_column(width=9, justify="right")     # est_ppt
    body.add_column(width=9, justify="right")     # e2e_ttft
    body.add_column(width=16, justify="right")    # runs / status
    if scrollable:
        body.add_column(width=1)                  # scrollbar
    return body


def _format_cell_row(slot: SlotState, ck: CellKey, cell: CellAggregate) -> List[Text]:
    done = cell.completed
    errors = cell.errors
    empty = cell.empty
    in_flight = cell.in_flight

    pp_str = f"{cell.pp_tps_mean:>7.0f}" if cell.pp_tps_mean is not None else "    —  "
    tg_str = f"{cell.tg_tps_mean:>6.1f}" if cell.tg_tps_mean is not None else "   —  "
    peak_str = (
        f"{cell.peak_tg_mean:>6.1f}" if cell.peak_tg_mean is not None else "   —  "
    )
    ttfr_str = _ms(cell.ttfr_s_mean if cell.ttfr_s_mean is not None else cell.ttft_s_mean)
    est_str = _ms(cell.est_ppt_s_mean if cell.est_ppt_s_mean is not None else cell.ttft_s_mean)
    e2e_str = _ms(cell.ttft_s_mean)

    status_text, status_style = _runs_status(done, errors, empty, in_flight)

    return [
        Text("●", style=slot.color),
        Text(slot.label, style="white"),
        Text(f"{ck.pp:,}", style=slot.color),
        Text(f"{ck.tg:,}", style="white"),
        Text(f"{ck.depth:,}", style="white"),
        Text(f"{ck.concurrency}", style="white"),
        Text(pp_str, style="white"),
        Text(tg_str, style="white"),
        Text(peak_str, style="white"),
        Text(ttfr_str, style="white"),
        Text(est_str, style="white"),
        Text(e2e_str, style="white"),
        Text(status_text, style=status_style),
    ]


def _runs_status(done: int, errors: int, empty: int, in_flight: int) -> tuple:
    """Compose the runs-column glyph + style.

    Priority: errors > empty > in_flight > clean. The leftmost number is
    always `done` (successful runs with data) so it's directly comparable
    to llama-benchy's runs count when everything went well.
    """
    if errors > 0:
        return f"{done}/{done + errors + empty} ✗", "red"
    if empty > 0:
        return f"{done} ⚠ ({empty} empty)", "yellow"
    if in_flight > 0:
        return f"{done} …", "white"
    return f"{done}", "white"


def _scrollbar_geometry(
    *, visible_rows: int, total_rows: int, offset: int
) -> Tuple[int, int]:
    """Return (thumb_size_in_rows, thumb_start_row)."""
    if total_rows <= visible_rows or visible_rows <= 0:
        return visible_rows, 0
    thumb_size = max(1, round(visible_rows * visible_rows / total_rows))
    thumb_size = min(thumb_size, visible_rows)
    max_offset = total_rows - visible_rows
    if max_offset <= 0:
        return thumb_size, 0
    max_thumb_start = visible_rows - thumb_size
    thumb_start = round((offset / max_offset) * max_thumb_start)
    thumb_start = max(0, min(thumb_start, max_thumb_start))
    return thumb_size, thumb_start


def _ms(seconds: Optional[float]) -> str:
    if seconds is None:
        return "    —  "
    return f"{seconds * 1000:>7.1f}"
