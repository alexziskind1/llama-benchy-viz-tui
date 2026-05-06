"""LayoutSpec — renderer-agnostic spatial composition.

A ``LayoutSpec`` describes WHERE modules go for a given dashboard mode.
The renderer is free to interpret regions as it sees fit (Rich.Layout for
TUI, CSS grid for web, native auto-layout for desktop) but must respect:

  - which modules are visible per mode
  - which modules belong in which region

Region IDs are conceptual, not coordinates. The conventional regions:

    HEADER          (top bar, full width)
    SUMMARY         (high-priority cards strip)
    MAIN_LEFT       (per-model detail / cards)
    MAIN_RIGHT      (chart)
    MAIN_RIGHT_BOTTOM (ranking / events, when present)
    DETAIL_BAND     (cells table, metadata, etc.)
    FOOTER          (mode badge + help)

Different modes use different subsets — see ``LAYOUTS`` below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .mode import DashboardMode


REGION_HEADER = "header"
REGION_SUMMARY = "summary"
REGION_MAIN_LEFT = "main_left"
REGION_MAIN_RIGHT = "main_right"
REGION_MAIN_RIGHT_BOTTOM = "main_right_bottom"
REGION_DETAIL_BAND = "detail_band"
REGION_FOOTER = "footer"


@dataclass(frozen=True)
class RegionSpec:
    """One region in the layout.

    ``module_ids`` lists the IDs of modules from the ViewModel that belong
    in this region (in order). The renderer looks up each ModuleSpec by
    ID. Some regions may host multiple modules side-by-side (see
    ``orientation``).
    """

    region_id: str
    module_ids: Tuple[str, ...] = ()
    orientation: str = "vertical"   # "vertical" | "horizontal"
    min_size: int = 0               # minimum rows (or cols if horizontal)
    weight: int = 1                 # relative weight in flexible parent


@dataclass(frozen=True)
class LayoutSpec:
    """Top-level layout for one dashboard mode."""

    mode: DashboardMode
    regions: Tuple[RegionSpec, ...]
    # Region IDs that should grow to fill the parent. Others get min_size only.
    flex_regions: Tuple[str, ...] = ()


# ─────────────────────────── module IDs ───────────────────────────────────
#
# Stable IDs used for both LayoutSpec wiring and ViewModel keys. The
# composer creates ModuleSpec instances with these IDs; the renderer
# looks them up by ID per region.

ID_HEADER = "header"
ID_SUMMARY = "summary"
ID_MODEL_CARD = "model_card"            # full-detail single model
ID_STREAM_GRID = "stream_grid"          # 2-4 stream cards (race)
ID_LIVE_CHART = "live_chart"
ID_STATIC_CHART = "static_chart"
ID_RANKING = "ranking"
ID_EVENTS = "events"
ID_CELLS = "cells_table"
ID_RUN_METADATA = "run_metadata"
ID_FOOTER = "footer"


# ─────────────────────────── per-mode layouts ─────────────────────────────


def _static_single() -> LayoutSpec:
    """Static single-model: focused, post-run summary."""
    return LayoutSpec(
        mode=DashboardMode.STATIC_SINGLE,
        regions=(
            RegionSpec(REGION_HEADER, (ID_HEADER,), min_size=3),
            RegionSpec(REGION_SUMMARY, (ID_SUMMARY,), min_size=5),
            RegionSpec(REGION_MAIN_LEFT, (ID_MODEL_CARD,), weight=1),
            RegionSpec(REGION_MAIN_RIGHT, (ID_STATIC_CHART,), weight=1),
            RegionSpec(REGION_DETAIL_BAND, (ID_CELLS, ID_RUN_METADATA),
                       orientation="horizontal", weight=1),
            RegionSpec(REGION_FOOTER, (ID_FOOTER,), min_size=3),
        ),
        flex_regions=(REGION_MAIN_LEFT, REGION_MAIN_RIGHT, REGION_DETAIL_BAND),
    )


def _static_race() -> LayoutSpec:
    """Static race: comparison-first, winner-first."""
    return LayoutSpec(
        mode=DashboardMode.STATIC_RACE,
        regions=(
            RegionSpec(REGION_HEADER, (ID_HEADER,), min_size=3),
            RegionSpec(REGION_SUMMARY, (ID_SUMMARY,), min_size=5),
            RegionSpec(REGION_MAIN_LEFT, (ID_STREAM_GRID,), weight=1),
            RegionSpec(REGION_MAIN_RIGHT, (ID_STATIC_CHART,), weight=1),
            RegionSpec(REGION_MAIN_RIGHT_BOTTOM, (ID_RANKING,), min_size=8),
            RegionSpec(REGION_DETAIL_BAND, (ID_RUN_METADATA,), weight=1),
            RegionSpec(REGION_FOOTER, (ID_FOOTER,), min_size=3),
        ),
        flex_regions=(REGION_MAIN_LEFT, REGION_MAIN_RIGHT, REGION_DETAIL_BAND),
    )


def _live_single() -> LayoutSpec:
    """Live single-model: progress-first, current-behavior-first."""
    return LayoutSpec(
        mode=DashboardMode.LIVE_SINGLE,
        regions=(
            RegionSpec(REGION_HEADER, (ID_HEADER,), min_size=3),
            RegionSpec(REGION_SUMMARY, (ID_SUMMARY,), min_size=5),
            RegionSpec(REGION_MAIN_LEFT, (ID_MODEL_CARD,), weight=1),
            RegionSpec(REGION_MAIN_RIGHT, (ID_LIVE_CHART,), weight=1),
            RegionSpec(REGION_DETAIL_BAND, (ID_CELLS,), weight=1),
            RegionSpec(REGION_FOOTER, (ID_FOOTER,), min_size=3),
        ),
        flex_regions=(REGION_MAIN_LEFT, REGION_MAIN_RIGHT, REGION_DETAIL_BAND),
    )


def _live_race() -> LayoutSpec:
    """Live race: visually rich, multiple streams + comparison."""
    return LayoutSpec(
        mode=DashboardMode.LIVE_RACE,
        regions=(
            RegionSpec(REGION_HEADER, (ID_HEADER,), min_size=3),
            RegionSpec(REGION_SUMMARY, (ID_SUMMARY,), min_size=5),
            RegionSpec(REGION_MAIN_LEFT, (ID_STREAM_GRID,), weight=1),
            RegionSpec(REGION_MAIN_RIGHT, (ID_LIVE_CHART,), weight=2),
            RegionSpec(REGION_MAIN_RIGHT_BOTTOM, (ID_RANKING, ID_EVENTS),
                       orientation="horizontal", min_size=8, weight=1),
            RegionSpec(REGION_FOOTER, (ID_FOOTER,), min_size=3),
        ),
        flex_regions=(REGION_MAIN_LEFT, REGION_MAIN_RIGHT),
    )


LAYOUTS: Dict[DashboardMode, LayoutSpec] = {
    DashboardMode.STATIC_SINGLE: _static_single(),
    DashboardMode.STATIC_RACE: _static_race(),
    DashboardMode.LIVE_SINGLE: _live_single(),
    DashboardMode.LIVE_RACE: _live_race(),
}


def for_mode(mode: DashboardMode) -> LayoutSpec:
    return LAYOUTS[mode]


def visible_module_ids(mode: DashboardMode) -> List[str]:
    """All module IDs visible in this mode, in layout order."""
    out: List[str] = []
    for r in LAYOUTS[mode].regions:
        out.extend(r.module_ids)
    return out
