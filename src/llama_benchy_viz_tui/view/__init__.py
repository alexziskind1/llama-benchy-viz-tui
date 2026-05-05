"""View layer — turn a domain Snapshot into a renderer-agnostic ViewModel.

Public API:

    from llama_benchy_viz_tui.view import build_view_model, DashboardMode, detect

    snap = state.snapshot()
    mode = override or detect(snap)
    view = build_view_model(snap, mode)
    renderer.render(view)

The ViewModel carries:
  - a typed `LayoutSpec` (which regions are visible for this mode)
  - a `dict[id → ModuleSpec]` describing what to show in each region
  - some `extras` (scroll state, flags) the renderer may consult

No Rich/UI imports here — the layer is renderer-agnostic.
"""

from .compose import ViewModel, build_view_model
from .layouts import LAYOUTS, LayoutSpec, RegionSpec, for_mode, visible_module_ids
from .mode import DashboardMode, detect, parse
from .modules import (
    CellRow,
    CellsTableSpec,
    ChartSeries,
    ChartSpec,
    EventLogEntry,
    EventLogSpec,
    FooterSpec,
    HeaderSpec,
    MetricValue,
    ModelMetricsCardSpec,
    ModuleSpec,
    RankingRow,
    RankingTableSpec,
    RunMetadataSpec,
    StreamCardSpec,
    StreamGridSpec,
    StreamRef,
    SummaryCard,
    SummaryStripSpec,
)

__all__ = [
    "CellRow",
    "CellsTableSpec",
    "ChartSeries",
    "ChartSpec",
    "DashboardMode",
    "EventLogEntry",
    "EventLogSpec",
    "FooterSpec",
    "HeaderSpec",
    "LAYOUTS",
    "LayoutSpec",
    "MetricValue",
    "ModelMetricsCardSpec",
    "ModuleSpec",
    "RankingRow",
    "RankingTableSpec",
    "RegionSpec",
    "RunMetadataSpec",
    "StreamCardSpec",
    "StreamGridSpec",
    "StreamRef",
    "SummaryCard",
    "SummaryStripSpec",
    "ViewModel",
    "build_view_model",
    "detect",
    "for_mode",
    "parse",
    "visible_module_ids",
]
