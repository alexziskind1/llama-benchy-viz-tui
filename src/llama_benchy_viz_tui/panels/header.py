"""Header panel: title / elapsed / benchmark name / active stream count."""

from __future__ import annotations

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..domain import Snapshot
from ._common import ACCENT, DIM, PANEL_BORDER, fmt_elapsed


def is_active(snap: Snapshot) -> bool:
    return True


def render(snap: Snapshot) -> RenderableType:
    title = Text("LLM BENCH ", style="bold white")
    title.append("VIZ", style=f"bold {ACCENT}")

    elapsed = Text()
    elapsed.append("⏱ ", style=DIM)
    elapsed.append(fmt_elapsed(snap.elapsed_s), style="bold white")
    elapsed.append("  ELAPSED", style=DIM)

    bench = Text()
    bench.append("◆ ", style=ACCENT)
    bench.append(snap.benchmark_name or "—", style="bold white")
    bench.append("  BENCHMARK", style=DIM)

    active = Text()
    active.append("⚡ ", style=ACCENT)
    active.append(f"{snap.active_count}/{snap.configured_count}", style="bold white")
    active.append("  ACTIVE", style=DIM)

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=2)
    table.add_column(ratio=1, justify="center")
    table.add_column(ratio=1, justify="center")
    table.add_column(ratio=1, justify="right")
    table.add_row(title, elapsed, bench, active)
    return Panel(table, border_style=PANEL_BORDER, padding=(0, 1))
