"""Renderer-agnostic ModuleSpec dataclasses.

Each ``*Spec`` is a typed view-model: pure data describing what to show,
with **no rendering primitives**. A TUI renderer maps these to Rich
widgets; a future web/native renderer maps them to its own primitives.

Composition flow:

    Snapshot (domain layer)
        │
        ▼  view.compose.build_view_model(snap, mode)
    ViewModel = LayoutSpec[ModuleSpec, …]
        │
        ▼  renderer.render(view_model)
    Frame on screen

The base ``ModuleSpec`` carries an ``id`` (for renderer caching) and a
``kind`` discriminator. Concrete subclasses add their own typed fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ───────────────────────── helpers ────────────────────────────────────────


@dataclass(frozen=True)
class MetricValue:
    """One numeric metric with an optional unit and label.

    ``value`` is ``None`` when the metric is unknown / not yet measured —
    renderers should display "—" or "N/A" in that case.
    """

    label: str
    value: Optional[float]
    unit: str = ""
    fmt: str = "{:.1f}"  # format string applied to value when not None

    def display(self) -> str:
        if self.value is None:
            return "—"
        return self.fmt.format(self.value) + (f" {self.unit}" if self.unit else "")


@dataclass(frozen=True)
class StreamRef:
    """Identifies one model run / slot for a renderer."""

    slot_index: int           # 0..3
    label: str                # human-friendly model name
    color: str                # CSS-hex (#ff3aa1 etc.)
    backend_kind: str = ""    # "CPU" / "GPU" / "" — informational badge


# ─────────────────────────── modules ──────────────────────────────────────


@dataclass(frozen=True)
class ModuleSpec:
    """Base class. Subclasses add typed fields."""

    id: str  # stable identity for caching/diffing in renderers
    kind: str = ""  # set by subclass

    def __post_init__(self) -> None:
        # Subclasses should override `kind` via field default.
        pass


@dataclass(frozen=True)
class HeaderSpec(ModuleSpec):
    """Title bar: session identity + elapsed + mode badge."""

    title: str = "LLM BENCH"
    accent: str = "VIZ"
    elapsed_s: float = 0.0
    benchmark_name: str = ""
    active_count: int = 0
    configured_count: int = 0
    mode_label: str = ""  # e.g. "LIVE · RACE"
    is_live: bool = False
    kind: str = "header"


@dataclass(frozen=True)
class SummaryCard:
    """One card in the SummaryStrip."""

    title: str               # e.g. "LEADER NOW", "BEST AVG", "FASTEST TTFT"
    icon: str = ""           # display icon, e.g. "🏆"
    icon_color: str = ""     # color hex for the icon
    primary: str = "—"       # main value (label of pick stream)
    primary_color: str = ""  # color hex applied to primary
    secondary: str = "—"     # subline (the metric value)


@dataclass(frozen=True)
class SummaryStripSpec(ModuleSpec):
    """The 3-up summary cards row across the top."""

    cards: Tuple[SummaryCard, ...] = ()
    kind: str = "summary_strip"


@dataclass(frozen=True)
class ModelMetricsCardSpec(ModuleSpec):
    """Full-detail card for a single model run.

    Used by static-single and live-single dashboards. Heavier than the
    competitor-style ``StreamCardSpec``.
    """

    stream: StreamRef = StreamRef(0, "", "")
    phase: str = ""                          # "PREFILL" / "DECODE" / "DONE" / etc.
    big_metric: MetricValue = field(default_factory=lambda: MetricValue("tok/s", None))
    metrics_grid: Tuple[Tuple[MetricValue, ...], ...] = ()
    sparkline: Tuple[float, ...] = ()
    output_snippet: str = ""
    show_phase: bool = True
    show_output: bool = True
    kind: str = "model_metrics_card"


@dataclass(frozen=True)
class StreamCardSpec(ModuleSpec):
    """Compact competitor card. Used by race dashboards.

    Same conceptual data as ``ModelMetricsCardSpec`` but compressed: the
    renderer is expected to render in roughly half the space because
    multiple cards sit side-by-side.
    """

    stream: StreamRef = StreamRef(0, "", "")
    phase: str = ""
    big_metric: MetricValue = field(default_factory=lambda: MetricValue("tok/s", None))
    metrics_grid: Tuple[Tuple[MetricValue, ...], ...] = ()
    sparkline: Tuple[float, ...] = ()
    output_snippet: str = ""
    show_phase: bool = True
    show_output: bool = True
    kind: str = "stream_card"


@dataclass(frozen=True)
class StreamGridSpec(ModuleSpec):
    """A grid of ``StreamCardSpec``s (race) or one ``ModelMetricsCardSpec``
    (single). Renderer decides whether to use 1×N, 2×2 etc."""

    cards: Tuple[ModuleSpec, ...] = ()  # ModelMetricsCardSpec | StreamCardSpec
    grid_shape: str = "auto"  # "auto" / "1x1" / "2x2" / "1xN"
    kind: str = "stream_grid"


@dataclass(frozen=True)
class ChartSeries:
    """One line on a chart."""

    label: str
    color: str
    points: Tuple[Tuple[float, float], ...] = ()  # (t_seconds, value)


@dataclass(frozen=True)
class ChartSpec(ModuleSpec):
    """Time-series chart, live or static.

    ``window_s`` controls the visible window:
      - live  → trailing window (e.g. 120 s back from `now`)
      - static → full run (renderer picks a fitting axis)
    """

    title: str = ""
    unit: str = "tok/s"
    series: Tuple[ChartSeries, ...] = ()
    now_s: float = 0.0
    window_s: Optional[float] = 120.0  # None = full run
    y_max: Optional[float] = None       # None = auto from data
    kind: str = "chart"


@dataclass(frozen=True)
class RankingRow:
    rank: int
    stream: StreamRef
    primary_metric: MetricValue
    delta_to_leader: Optional[float] = None  # absolute delta vs rank 1


@dataclass(frozen=True)
class RankingTableSpec(ModuleSpec):
    """Sorted leaderboard. Race-modes only."""

    title: str = "LIVE RANKING"
    subtitle: str = "(by avg tok/s)"
    rows: Tuple[RankingRow, ...] = ()
    higher_is_better: bool = True
    kind: str = "ranking_table"


@dataclass(frozen=True)
class EventLogEntry:
    ts: float
    stream_color: str = ""  # color of the slot for this event, "" for system
    label: str = ""
    text: str = ""


@dataclass(frozen=True)
class EventLogSpec(ModuleSpec):
    """Rolling event/audit log."""

    title: str = "EVENTS"
    subtitle: str = "(Live)"
    entries: Tuple[EventLogEntry, ...] = ()
    kind: str = "event_log"


@dataclass(frozen=True)
class CellRow:
    """One row in the cells table."""

    stream: StreamRef
    pp: int
    tg: int
    depth: int
    concurrency: int
    pp_tps: Optional[float]
    tg_tps: Optional[float]
    peak_tg: Optional[float]
    ttfr_ms: Optional[float]
    est_ppt_ms: Optional[float]
    e2e_ttft_ms: Optional[float]
    runs_done: int
    runs_in_flight: int
    runs_empty: int
    runs_errored: int


@dataclass(frozen=True)
class CellsTableSpec(ModuleSpec):
    """Per-cell results table (one row per (pp,tg,depth,concurrency))."""

    title: str = "BENCHMARK CELLS"
    rows: Tuple[CellRow, ...] = ()
    scroll_offset: int = 0
    kind: str = "cells_table"


@dataclass(frozen=True)
class RunMetadataSpec(ModuleSpec):
    """Producer info, latency, latency mode, etc."""

    producer_version: str = ""
    schema_version: str = ""
    latency_ms: Optional[float] = None
    latency_mode: str = ""
    started_ts: float = 0.0
    finished_ts: float = 0.0
    kind: str = "run_metadata"


@dataclass(frozen=True)
class FooterSpec(ModuleSpec):
    """Mode indicator + status + help."""

    mode_label: str = ""
    status: str = "LIVE"     # or "FROZEN"
    schema_version: str = ""
    producer_version: str = ""
    quit_hint: str = "Ctrl+C"
    kind: str = "footer"
