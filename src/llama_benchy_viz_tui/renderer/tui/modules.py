"""TUI module renderers.

One ``render_<kind>(spec, **opts)`` function per ModuleSpec kind. Each is
a pure ModuleSpec → Rich Renderable mapping; no domain or ingest
imports. The layout adapter walks the LayoutSpec and dispatches to the
right renderer based on ``spec.kind``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.align import Align
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...chart import render_chart, render_sparkline
from ...view.modules import (
    CellsTableSpec,
    ChartSpec,
    EventLogSpec,
    FooterSpec,
    HeaderSpec,
    MetricValue,
    ModelMetricsCardSpec,
    ModuleSpec,
    RankingTableSpec,
    RunMetadataSpec,
    StreamCardSpec,
    StreamGridSpec,
    SummaryStripSpec,
)


# ─────────────────────────── visual constants ────────────────────────────

ACCENT = "#39ff7a"
PANEL_BORDER = "grey30"
DIM = "grey50"


def _fmt_elapsed(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def _phase_badge(phase: str, color: str) -> Text:
    style_map = {
        "LOADING": ("LOADING", "black on grey50"),
        "PREFILL": ("PREFILL", f"black on {ACCENT}"),
        "DECODE": ("DECODE", f"black on {color}"),
        "DONE": ("DONE", "black on grey70"),
        "ERROR": ("ERROR", "white on red"),
    }
    label, style = style_map.get(phase, (phase, "white"))
    return Text(f" {label} ", style=style)


def _metric_text(m: MetricValue, fmt_override: Optional[str] = None) -> Text:
    """Render `LABEL  value [unit]` as a Text run."""
    out = Text()
    out.append(f"{m.label} ", style=DIM)
    if m.value is None:
        out.append("N/A", style="white")
    else:
        fmt = fmt_override or m.fmt
        out.append(fmt.format(m.value), style="white")
        if m.unit:
            out.append(f" {m.unit}", style="white")
    return out


# ─────────────────────────── header ──────────────────────────────────────


def render_header(spec: HeaderSpec) -> RenderableType:
    title = Text("LLM BENCH ", style="bold white")
    title.append(spec.accent, style=f"bold {ACCENT}")

    elapsed = Text()
    elapsed.append("⏱ ", style=DIM)
    elapsed.append(_fmt_elapsed(spec.elapsed_s), style="bold white")
    elapsed.append("  ELAPSED", style=DIM)

    bench = Text()
    bench.append("◆ ", style=ACCENT)
    bench.append(spec.benchmark_name or "—", style="bold white")
    bench.append("  BENCHMARK", style=DIM)

    active = Text()
    active.append("⚡ ", style=ACCENT)
    active.append(f"{spec.active_count}/{spec.configured_count}", style="bold white")
    active.append("  ACTIVE", style=DIM)

    mode_badge = Text()
    if spec.mode_label:
        bg = ACCENT if spec.is_live else "grey50"
        mode_badge.append(f" {spec.mode_label} ", style=f"black on {bg}")

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=2)
    grid.add_column(ratio=1, justify="center")
    grid.add_column(ratio=1, justify="center")
    grid.add_column(ratio=1, justify="right")
    grid.add_column(width=20, justify="right")
    grid.add_row(title, elapsed, bench, active, mode_badge)
    return Panel(grid, border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── summary strip ───────────────────────────────


def render_summary_strip(spec: SummaryStripSpec) -> RenderableType:
    panels = []
    for card in spec.cards:
        head = Text()
        if card.icon:
            head.append(f"{card.icon} ", style=card.icon_color or DIM)
        head.append(card.title, style=DIM)
        primary_style = (
            f"bold {card.primary_color}" if card.primary_color else "bold white"
        )
        body = Text(card.primary, style=primary_style)
        sub = Text(card.secondary, style="bold white")
        panels.append(
            Panel(Group(head, body, sub), border_style=PANEL_BORDER, padding=(0, 1))
        )

    grid = Table.grid(expand=True, padding=(0, 1))
    for _ in panels:
        grid.add_column(ratio=1)
    grid.add_row(*panels)
    return grid


# ─────────────────────────── stream card / model card ────────────────────


def _render_card(spec, *, is_compact: bool) -> Panel:
    """Shared body for ModelMetricsCardSpec and StreamCardSpec.

    ``is_compact`` lets the race-style stream cards drop the output-snippet
    line so 4 cards fit in the same vertical space the single mode gives
    one card.
    """
    color = spec.stream.color or "white"

    head = Table.grid(expand=True, padding=(0, 1))
    head.add_column(width=3)
    head.add_column(ratio=1)
    slot_badge = Text(f" {spec.stream.slot_index + 1} ", style=f"black on {color}")
    label = Text(spec.stream.label or f"slot {spec.stream.slot_index + 1}",
                 style="bold white")
    head.add_row(slot_badge, label)

    rows = [head]

    if spec.show_phase or spec.sparkline:
        phase_row = Table.grid(expand=True, padding=(0, 1))
        phase_row.add_column()
        phase_row.add_column(ratio=1, justify="right")
        phase_cell = _phase_badge(spec.phase, color) if spec.show_phase else Text("")
        spark = (
            render_sparkline(list(spec.sparkline), color, width=18)
            if spec.sparkline
            else Text("")
        )
        phase_row.add_row(phase_cell, spark)
        rows.append(phase_row)

    big = Text()
    if spec.big_metric.value is None:
        big.append("  —  ", style=f"bold {color}")
    else:
        big.append(spec.big_metric.fmt.format(spec.big_metric.value),
                   style=f"bold {color}")
    if spec.big_metric.unit:
        big.append(f" {spec.big_metric.unit}", style="white")
    rows.append(big)

    if spec.metrics_grid:
        for row in spec.metrics_grid:
            rgrid = Table.grid(expand=True, padding=(0, 1))
            for _ in row:
                rgrid.add_column(ratio=1)
            rgrid.add_row(*[_metric_text(m) for m in row])
            rows.append(rgrid)

    if spec.show_output and not is_compact:
        snip = Text()
        snip.append("OUTPUT > ", style=DIM)
        text = (spec.output_snippet or "…")[-180:].replace("\n", " ")
        snip.append(text, style="grey70")
        rows.append(snip)

    return Panel(Group(*rows), border_style=color, padding=(0, 1))


def render_model_metrics_card(spec: ModelMetricsCardSpec) -> RenderableType:
    return _render_card(spec, is_compact=False)


def render_stream_card(spec: StreamCardSpec) -> RenderableType:
    return _render_card(spec, is_compact=True)


def render_stream_grid(spec: StreamGridSpec) -> RenderableType:
    """Compose 1-4 stream cards into a 1xN or 2x2 grid.

    Uses placeholders to keep the grid shape stable when fewer than 4
    streams are present.
    """
    cards = list(spec.cards)
    while len(cards) < 4:
        cards.append(None)

    placeholder = Panel(
        Align.center(Text("(no stream)", style=DIM), vertical="middle"),
        border_style=PANEL_BORDER,
        padding=(0, 1),
    )

    rendered = [
        render_stream_card(c) if isinstance(c, StreamCardSpec) else placeholder
        for c in cards
    ]

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(rendered[0], rendered[1])
    grid.add_row(rendered[2], rendered[3])
    return grid


# ─────────────────────────── chart ───────────────────────────────────────


def render_chart_module(
    spec: ChartSpec,
    *,
    width: int = 100,
    height: int = 12,
) -> RenderableType:
    title = Table.grid(expand=True)
    title.add_column(ratio=1)
    title.add_column(justify="right")
    title.add_row(
        Text(spec.title or "PERFORMANCE", style="bold white"),
        Text(spec.unit, style=DIM),
    )

    series_arg = [(s.label, s.color, list(s.points)) for s in spec.series]
    chart_text = render_chart(
        series_arg,
        width=width,
        height=max(8, height),
        history_seconds=spec.window_s if spec.window_s is not None else 1e9,
        now=spec.now_s,
        y_max=spec.y_max,
    )
    return Panel(Group(title, chart_text), border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── ranking ─────────────────────────────────────


def render_ranking(spec: RankingTableSpec) -> RenderableType:
    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text(spec.title, style="bold white"),
        Text(spec.subtitle, style=DIM),
    )

    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=4)
    body.add_column(ratio=1)
    body.add_column(width=14, justify="right")
    body.add_column(width=12, justify="right")

    if not spec.rows:
        body.add_row(Text("—", style=DIM), Text("waiting…", style=DIM), Text(""), Text(""))
    else:
        for row in spec.rows[:6]:
            delta_str = ""
            if row.delta_to_leader is not None and row.rank > 1:
                delta_str = f"{row.delta_to_leader:+.1f}"
            body.add_row(
                Text(f"#{row.rank}", style="bold white"),
                Text(row.stream.label, style=row.stream.color),
                Text(row.primary_metric.display(), style="white"),
                Text(delta_str, style=DIM),
            )
    foot = Text(
        "Higher avg tok/s is better" if spec.higher_is_better else "Lower is better",
        style=DIM,
    )
    return Panel(Group(head, body, foot), border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── events ──────────────────────────────────────


def render_events(spec: EventLogSpec) -> RenderableType:
    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text(spec.title, style="bold white"),
        Text(spec.subtitle, style=DIM),
    )

    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=10)
    body.add_column()

    if not spec.entries:
        body.add_row(Text("—", style=DIM), Text("waiting…", style=DIM))
    else:
        for ev in spec.entries[-7:]:
            ts = datetime.fromtimestamp(ev.ts).strftime("%H:%M:%S")
            line = Text()
            color = ev.stream_color or "white"
            line.append("● ", style=color)
            line.append(f"{ev.label} ", style=color)
            line.append(ev.text, style="white")
            body.add_row(Text(ts, style=DIM), line)
    foot = Text("Showing latest events…", style=DIM)
    return Panel(Group(head, body, foot), border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── cells table ─────────────────────────────────


def render_cells_table(
    spec: CellsTableSpec,
    *,
    max_data_rows: Optional[int] = None,
) -> RenderableType:
    n = len(spec.rows)
    visible = max_data_rows if max_data_rows is not None else n
    visible = max(1, min(visible, n)) if n else visible
    scrollable = n > visible

    if scrollable:
        max_offset = n - visible
        offset = max(0, min(spec.scroll_offset, max_offset))
        slice_lo, slice_hi = offset, offset + visible
    else:
        offset = 0
        slice_lo, slice_hi = 0, n

    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    if scrollable:
        right = Text(
            f"showing {slice_lo + 1}-{slice_hi} of {n}   "
            "↑/↓ scroll  PgUp/PgDn page  g/G top/bottom",
            style="yellow",
        )
    else:
        right = Text("(per-cell results)", style=DIM)
    head.add_row(Text(spec.title, style="bold white"), right)

    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=2)              # color dot
    body.add_column(ratio=2)              # stream
    body.add_column(width=7, justify="right")     # pp
    body.add_column(width=7, justify="right")     # tg
    body.add_column(width=7, justify="right")     # depth
    body.add_column(width=5, justify="right")     # conc
    body.add_column(width=10, justify="right")    # pp tok/s
    body.add_column(width=10, justify="right")    # tg tok/s
    body.add_column(width=9, justify="right")     # peak tg
    body.add_column(width=10, justify="right")    # ttfr
    body.add_column(width=9, justify="right")     # est_ppt
    body.add_column(width=9, justify="right")     # e2e_ttft
    body.add_column(width=16, justify="right")    # runs/status
    if scrollable:
        body.add_column(width=1)

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
        header_cells.append(Text(" "))
    body.add_row(*header_cells)

    if not spec.rows:
        empty_row = [Text("")] * (13 + (1 if scrollable else 0))
        empty_row[1] = Text("waiting…", style=DIM)
        body.add_row(*empty_row)
        return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))

    if scrollable:
        thumb_size, thumb_start = _scrollbar_geometry(visible, n, offset)

    for i, row in enumerate(spec.rows[slice_lo:slice_hi]):
        pp_str = f"{row.pp_tps:>7.0f}" if row.pp_tps is not None else "    —  "
        tg_str = f"{row.tg_tps:>6.1f}" if row.tg_tps is not None else "   —  "
        peak_str = f"{row.peak_tg:>6.1f}" if row.peak_tg is not None else "   —  "
        ttfr_str = _ms(row.ttfr_ms)
        est_str = _ms(row.est_ppt_ms)
        e2e_str = _ms(row.e2e_ttft_ms)
        status_text, status_style = _runs_status(
            row.runs_done, row.runs_errored, row.runs_empty, row.runs_in_flight
        )

        cells = [
            Text("●", style=row.stream.color),
            Text(row.stream.label, style="white"),
            Text(f"{row.pp:,}", style=row.stream.color),
            Text(f"{row.tg:,}", style="white"),
            Text(f"{row.depth:,}", style="white"),
            Text(f"{row.concurrency}", style="white"),
            Text(pp_str, style="white"),
            Text(tg_str, style="white"),
            Text(peak_str, style="white"),
            Text(ttfr_str, style="white"),
            Text(est_str, style="white"),
            Text(e2e_str, style="white"),
            Text(status_text, style=status_style),
        ]
        if scrollable:
            in_thumb = thumb_start <= i < thumb_start + thumb_size
            cells.append(Text("█" if in_thumb else "░",
                              style="grey50" if in_thumb else "grey23"))
        body.add_row(*cells)

    return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))


def _ms(value_ms: Optional[float]) -> str:
    if value_ms is None:
        return "    —  "
    return f"{value_ms:>7.1f}"


def _runs_status(done: int, errors: int, empty: int, in_flight: int):
    if errors > 0:
        return f"{done}/{done + errors + empty} ✗", "red"
    if empty > 0:
        return f"{done} ⚠ ({empty} empty)", "yellow"
    if in_flight > 0:
        return f"{done} …", "white"
    return f"{done}", "white"


def _scrollbar_geometry(visible_rows: int, total_rows: int, offset: int):
    if total_rows <= visible_rows or visible_rows <= 0:
        return visible_rows, 0
    thumb_size = max(1, round(visible_rows * visible_rows / total_rows))
    thumb_size = min(thumb_size, visible_rows)
    max_offset = total_rows - visible_rows
    if max_offset <= 0:
        return thumb_size, 0
    max_thumb_start = visible_rows - thumb_size
    thumb_start = round((offset / max_offset) * max_thumb_start)
    return thumb_size, max(0, min(thumb_start, max_thumb_start))


# ─────────────────────────── run metadata ────────────────────────────────


def render_run_metadata(spec: RunMetadataSpec) -> RenderableType:
    head = Text("RUN METADATA", style="bold white")
    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(width=14, justify="right")
    body.add_column(ratio=1)

    def add(k: str, v: str) -> None:
        body.add_row(Text(k, style=DIM), Text(v, style="white"))

    add("producer", spec.producer_version or "—")
    add("schema", spec.schema_version or "—")
    add("latency",
        f"{spec.latency_ms:.2f} ms ({spec.latency_mode})"
        if spec.latency_ms is not None else "—")
    if spec.started_ts:
        add("started", datetime.fromtimestamp(spec.started_ts).strftime("%H:%M:%S"))
    if spec.finished_ts:
        add("finished", datetime.fromtimestamp(spec.finished_ts).strftime("%H:%M:%S"))
        if spec.started_ts:
            duration = max(0.0, spec.finished_ts - spec.started_ts)
            add("duration", _fmt_elapsed(duration))
    return Panel(Group(head, body), border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── footer ──────────────────────────────────────


def render_footer(spec: FooterSpec) -> RenderableType:
    line = Text()
    line.append("schema: ", style=DIM)
    line.append(spec.schema_version or "—", style="white")
    line.append("    producer: ", style=DIM)
    line.append(spec.producer_version or "—", style="white")
    line.append("    mode: ", style=DIM)
    line.append(spec.mode_label or "—", style="white")
    line.append("    status: ", style=DIM)
    is_live = spec.status.upper() == "LIVE"
    line.append(spec.status, style=ACCENT if is_live else "yellow")
    line.append("    quit: ", style=DIM)
    line.append(spec.quit_hint, style="white")
    return Panel(line, border_style=PANEL_BORDER, padding=(0, 1))


# ─────────────────────────── dispatch ────────────────────────────────────


def render_module(
    spec: ModuleSpec,
    *,
    width: int = 100,
    height: int = 12,
    max_data_rows: Optional[int] = None,
) -> RenderableType:
    """Dispatch one ModuleSpec to the right renderer."""
    kind = spec.kind
    if kind == "header":
        return render_header(spec)  # type: ignore[arg-type]
    if kind == "summary_strip":
        return render_summary_strip(spec)  # type: ignore[arg-type]
    if kind == "model_metrics_card":
        return render_model_metrics_card(spec)  # type: ignore[arg-type]
    if kind == "stream_card":
        return render_stream_card(spec)  # type: ignore[arg-type]
    if kind == "stream_grid":
        return render_stream_grid(spec)  # type: ignore[arg-type]
    if kind == "chart":
        return render_chart_module(spec, width=width, height=height)  # type: ignore[arg-type]
    if kind == "ranking_table":
        return render_ranking(spec)  # type: ignore[arg-type]
    if kind == "event_log":
        return render_events(spec)  # type: ignore[arg-type]
    if kind == "cells_table":
        return render_cells_table(spec, max_data_rows=max_data_rows)  # type: ignore[arg-type]
    if kind == "run_metadata":
        return render_run_metadata(spec)  # type: ignore[arg-type]
    if kind == "footer":
        return render_footer(spec)  # type: ignore[arg-type]
    return Panel(Text(f"unknown module kind: {kind}", style="red"))
