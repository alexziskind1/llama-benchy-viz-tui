"""View-model composer.

Takes a domain ``Snapshot`` and a ``DashboardMode``, produces a
``ViewModel`` — a flat dict of ModuleSpec keyed by ID, plus the LayoutSpec
that tells the renderer where to put each one.

Modes pick different module sets and parameterize them differently:

  - live charts use rolling windows; static charts use full history
  - live summary cards say "LEADER NOW"; static says "BEST AVG (winner)"
  - race modes use ``StreamGridSpec`` of compact ``StreamCardSpec``s;
    single modes use a single full-detail ``ModelMetricsCardSpec``
  - cells table is shown post-run for static-single (full sweep) and
    progressively for live-single (live sweep); not shown in race
    (race is about now/comparison, not detailed per-cell stats)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..domain import (
    CHART_HISTORY_S,
    AppState,
    CellAggregate,
    CellKey,
    EventEntry,
    SlotState,
    Snapshot,
)
from .layouts import (
    ID_CELLS,
    ID_EVENTS,
    ID_FOOTER,
    ID_HEADER,
    ID_LIVE_CHART,
    ID_MODEL_CARD,
    ID_RANKING,
    ID_RUN_METADATA,
    ID_STATIC_CHART,
    ID_STREAM_GRID,
    ID_SUMMARY,
    LayoutSpec,
    for_mode,
)
from .mode import DashboardMode
from .modules import (
    CellRow,
    ChartSeries,
    ChartSpec,
    EventLogEntry,
    EventLogSpec,
    FooterSpec,
    HeaderSpec,
    ModelMetricsCardSpec,
    ModuleSpec,
    MetricValue,
    RankingRow,
    RankingTableSpec,
    RunMetadataSpec,
    StreamCardSpec,
    StreamGridSpec,
    StreamRef,
    SummaryCard,
    SummaryStripSpec,
)


@dataclass(frozen=True)
class ViewModel:
    """The complete view-model for one rendered frame."""

    mode: DashboardMode
    layout: LayoutSpec
    modules: Dict[str, ModuleSpec]
    # Renderer-relevant snapshot bits that aren't a "module" (e.g. scroll
    # state). Keep this dict-shaped so future renderers can ignore keys
    # they don't understand.
    extras: Dict[str, object]


# ──────────────────────────── public entry point ──────────────────────────


def build_view_model(snap: Snapshot, mode: DashboardMode) -> ViewModel:
    """Compose a ViewModel for the given mode from a domain Snapshot."""
    layout = for_mode(mode)
    visible = {r.region_id: r.module_ids for r in layout.regions}
    needed = {mid for ids in visible.values() for mid in ids}

    modules: Dict[str, ModuleSpec] = {}

    if ID_HEADER in needed:
        modules[ID_HEADER] = _header(snap, mode)
    if ID_SUMMARY in needed:
        modules[ID_SUMMARY] = _summary(snap, mode)
    if ID_MODEL_CARD in needed:
        modules[ID_MODEL_CARD] = _model_card(snap, mode)
    if ID_STREAM_GRID in needed:
        modules[ID_STREAM_GRID] = _stream_grid(snap, mode)
    if ID_LIVE_CHART in needed:
        modules[ID_LIVE_CHART] = _chart(snap, mode, live=True)
    if ID_STATIC_CHART in needed:
        modules[ID_STATIC_CHART] = _chart(snap, mode, live=False)
    if ID_RANKING in needed:
        modules[ID_RANKING] = _ranking(snap, mode)
    if ID_EVENTS in needed:
        modules[ID_EVENTS] = _events(snap, mode)
    if ID_CELLS in needed:
        modules[ID_CELLS] = _cells(snap, mode)
    if ID_RUN_METADATA in needed:
        modules[ID_RUN_METADATA] = _run_metadata(snap, mode)
    if ID_FOOTER in needed:
        modules[ID_FOOTER] = _footer(snap, mode)

    return ViewModel(
        mode=mode,
        layout=layout,
        modules=modules,
        extras={
            "cells_scroll_offset": snap.cells_scroll_offset,
            "show_events": snap.show_events,
        },
    )


# ──────────────────────────── module builders ─────────────────────────────


def _stream_ref(slot: SlotState) -> StreamRef:
    return StreamRef(
        slot_index=slot.slot,
        label=slot.label or f"slot {slot.slot + 1}",
        color=slot.color,
        backend_kind="",
    )


def _mode_label(mode: DashboardMode) -> str:
    return {
        DashboardMode.STATIC_SINGLE: "STATIC · SINGLE",
        DashboardMode.STATIC_RACE: "STATIC · RACE",
        DashboardMode.LIVE_SINGLE: "LIVE · SINGLE",
        DashboardMode.LIVE_RACE: "LIVE · RACE",
    }[mode]


def _header(snap: Snapshot, mode: DashboardMode) -> HeaderSpec:
    return HeaderSpec(
        id=ID_HEADER,
        elapsed_s=snap.elapsed_s,
        benchmark_name=snap.benchmark_name or "—",
        active_count=snap.active_count,
        configured_count=snap.configured_count,
        mode_label=_mode_label(mode),
        is_live=mode.is_live,
    )


def _summary(snap: Snapshot, mode: DashboardMode) -> SummaryStripSpec:
    """Three cards. Labels swap to winner-flavor in static modes."""
    leader = snap.leader_now()
    best = snap.best_avg()
    fastest = snap.fastest_ttft()
    is_static = not mode.is_live

    leader_label = "BEST PEAK" if is_static else "LEADER NOW"
    leader_card = SummaryCard(
        title=leader_label,
        icon="🏆",
        icon_color="#ffb000",
        primary=leader.label if leader else "—",
        primary_color=leader.color if leader else "",
        secondary=(
            f"{leader.current_tps:.1f} tok/s" if leader else "—"
        ),
    )
    best_card = SummaryCard(
        title="BEST AVG",
        icon="★",
        icon_color="#a96bff",
        primary=best.label if best else "—",
        primary_color=best.color if best else "",
        secondary=f"{best.avg_tps:.1f} tok/s" if best else "—",
    )
    fast_card = SummaryCard(
        title="FASTEST TTFT",
        icon="⚡",
        icon_color="#39ff7a",
        primary=fastest.label if fastest else "—",
        primary_color=fastest.color if fastest else "",
        secondary=(
            f"{fastest.last_ttft_s:.2f} s"
            if fastest and fastest.last_ttft_s is not None
            else "—"
        ),
    )
    return SummaryStripSpec(
        id=ID_SUMMARY,
        cards=(leader_card, best_card, fast_card),
    )


def _metrics_grid(slot: SlotState) -> Tuple[Tuple[MetricValue, ...], ...]:
    """3×2 metric grid used by both ModelMetricsCard and StreamCard."""
    row1 = (
        MetricValue("AVG", slot.avg_tps, "tok/s", "{:5.1f}"),
        MetricValue(
            "TTFT",
            slot.last_ttft_s,
            "s",
            "{:.2f}",
        ),
        MetricValue(
            "PP",
            slot.last_pp_tps,
            "tok/s",
            "{:.0f}",
        ),
    )
    row2 = (
        MetricValue("GEN", float(slot.total_gen_tokens), "", "{:,.0f}"),
        MetricValue(
            "PROMPT",
            float(slot.last_prompt_tokens),
            "",
            "{:,.0f}",
        ),
        MetricValue("CONC", float(slot.concurrency or 1), "", "{:.0f}"),
    )
    return (row1, row2)


def _model_card(snap: Snapshot, mode: DashboardMode) -> ModelMetricsCardSpec:
    """Single full-detail card (single-model modes)."""
    if not snap.slots:
        # Empty placeholder
        return ModelMetricsCardSpec(
            id=ID_MODEL_CARD,
            stream=StreamRef(0, "—", "grey50"),
            phase="",
            big_metric=MetricValue("tok/s", None),
            metrics_grid=(),
            sparkline=(),
            output_snippet="",
            show_phase=mode.is_live,
            show_output=mode.is_live,
        )
    slot = snap.slots[0]
    return ModelMetricsCardSpec(
        id=ID_MODEL_CARD,
        stream=_stream_ref(slot),
        phase=slot.phase,
        big_metric=MetricValue(
            "tok/s",
            slot.current_tps if mode.is_live else slot.avg_tps,
            "tok/s",
            "{:5.1f}",
        ),
        metrics_grid=_metrics_grid(slot),
        sparkline=tuple(slot.sparkline),
        output_snippet=slot.output_snippet if mode.is_live else "",
        show_phase=mode.is_live,
        show_output=mode.is_live,
    )


def _stream_grid(snap: Snapshot, mode: DashboardMode) -> StreamGridSpec:
    """Race grid: 2-4 compact stream cards."""
    cards: List[ModuleSpec] = []
    for slot in snap.slots:
        cards.append(
            StreamCardSpec(
                id=f"stream_{slot.slot}",
                stream=_stream_ref(slot),
                phase=slot.phase,
                big_metric=MetricValue(
                    "tok/s",
                    slot.current_tps if mode.is_live else slot.avg_tps,
                    "tok/s",
                    "{:5.1f}",
                ),
                metrics_grid=_metrics_grid(slot),
                sparkline=tuple(slot.sparkline),
                output_snippet=slot.output_snippet if mode.is_live else "",
                show_phase=mode.is_live,
                show_output=mode.is_live,
            )
        )
    return StreamGridSpec(
        id=ID_STREAM_GRID,
        cards=tuple(cards),
        grid_shape="2x2" if len(cards) > 2 else "1xN",
    )


def _chart(snap: Snapshot, mode: DashboardMode, *, live: bool) -> ChartSpec:
    series = tuple(
        ChartSeries(
            label=s.label or f"slot {s.slot + 1}",
            color=s.color,
            points=tuple(s.history),
        )
        for s in snap.slots
    )
    title = "LIVE PERFORMANCE" if live else "PERFORMANCE — FINAL"
    return ChartSpec(
        id=ID_LIVE_CHART if live else ID_STATIC_CHART,
        title=title,
        unit="tok/s",
        series=series,
        now_s=snap.last_event_ts or 0.0,
        window_s=CHART_HISTORY_S if live else None,
        y_max=snap.chart_y_max,
    )


def _ranking(snap: Snapshot, mode: DashboardMode) -> RankingTableSpec:
    rows: List[RankingRow] = []
    sorted_slots = snap.ranking_by_avg()
    leader_avg = sorted_slots[0].avg_tps if sorted_slots else 0.0
    for i, s in enumerate(sorted_slots[:6], start=1):
        rows.append(
            RankingRow(
                rank=i,
                stream=_stream_ref(s),
                primary_metric=MetricValue("avg", s.avg_tps, "tok/s", "{:.1f}"),
                delta_to_leader=(s.avg_tps - leader_avg) if leader_avg else None,
            )
        )
    title = "FINAL RANKING" if not mode.is_live else "LIVE RANKING"
    return RankingTableSpec(
        id=ID_RANKING,
        title=title,
        subtitle="(by avg tok/s)",
        rows=tuple(rows),
        higher_is_better=True,
    )


def _events(snap: Snapshot, mode: DashboardMode) -> EventLogSpec:
    entries: List[EventLogEntry] = []
    for ev in snap.events[-20:]:
        color = ""
        if ev.slot is not None:
            for s in snap.slots:
                if s.slot == ev.slot:
                    color = s.color
                    break
        entries.append(
            EventLogEntry(ts=ev.ts, stream_color=color, label=ev.label, text=ev.text)
        )
    return EventLogSpec(
        id=ID_EVENTS,
        title="EVENTS",
        subtitle="(Live)" if mode.is_live else "(Final)",
        entries=tuple(entries),
    )


def _cells(snap: Snapshot, mode: DashboardMode) -> "ModuleSpec":
    """Per-cell results table. Renderer handles scroll/truncation."""
    from .modules import CellsTableSpec

    rows: List[CellRow] = []
    for slot in snap.slots:
        for ck in sorted(
            slot.cells.keys(),
            key=lambda k: (k.pp, k.tg, k.depth, k.concurrency),
        ):
            cell = slot.cells[ck]
            rows.append(
                CellRow(
                    stream=_stream_ref(slot),
                    pp=ck.pp,
                    tg=ck.tg,
                    depth=ck.depth,
                    concurrency=ck.concurrency,
                    pp_tps=cell.pp_tps_mean,
                    tg_tps=cell.tg_tps_mean,
                    peak_tg=cell.peak_tg_mean,
                    ttfr_ms=(cell.ttfr_s_mean or cell.ttft_s_mean) * 1000.0
                    if (cell.ttfr_s_mean or cell.ttft_s_mean) is not None
                    else None,
                    est_ppt_ms=(cell.est_ppt_s_mean or cell.ttft_s_mean) * 1000.0
                    if (cell.est_ppt_s_mean or cell.ttft_s_mean) is not None
                    else None,
                    e2e_ttft_ms=cell.ttft_s_mean * 1000.0
                    if cell.ttft_s_mean is not None
                    else None,
                    runs_done=cell.completed,
                    runs_in_flight=cell.in_flight,
                    runs_empty=cell.empty,
                    runs_errored=cell.errors,
                )
            )
    return CellsTableSpec(
        id=ID_CELLS,
        title="BENCHMARK CELLS",
        rows=tuple(rows),
        scroll_offset=snap.cells_scroll_offset,
    )


def _run_metadata(snap: Snapshot, mode: DashboardMode) -> RunMetadataSpec:
    return RunMetadataSpec(
        id=ID_RUN_METADATA,
        producer_version=snap.llama_benchy_version or "unknown",
        schema_version="llama-benchy-progress.v1",
        latency_ms=(snap.latency_s * 1000.0) if snap.latency_s is not None else None,
        latency_mode=snap.latency_mode,
        started_ts=snap.started_ts,
        finished_ts=snap.last_event_ts if snap.finished else 0.0,
    )


def _footer(snap: Snapshot, mode: DashboardMode) -> FooterSpec:
    return FooterSpec(
        id=ID_FOOTER,
        mode_label=_mode_label(mode),
        status="FROZEN" if snap.finished else "LIVE",
        schema_version="llama-benchy-progress.v1",
        producer_version=snap.llama_benchy_version or "unknown",
        quit_hint="Ctrl+C",
    )
