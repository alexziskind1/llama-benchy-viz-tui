"""TUI layout adapter — turn a ViewModel into a Rich Layout.

This is where the abstract LayoutSpec regions become concrete vertical
splits in a Rich Layout tree. The wiring rules:

  HEADER / SUMMARY / FOOTER       → fixed-height rows at top/middle/bottom
  MAIN_LEFT + MAIN_RIGHT          → horizontal split inside MAIN
  MAIN_RIGHT_BOTTOM               → vertical split inside MAIN_RIGHT
  DETAIL_BAND                     → row above FOOTER, sized to its content
                                    (cells panel asks for `min_height`)

When a region has multiple modules with ``orientation="horizontal"``,
they sit side-by-side. ``"vertical"`` stacks them.

The composer asks each module for an optional ``min_height`` (only
``cells_table`` provides it today) and reserves enough room before
deciding the main grid's flexible size.
"""

from __future__ import annotations

from typing import Dict, Optional

from rich.console import RenderableType
from rich.layout import Layout

from ...view import LayoutSpec, RegionSpec, ViewModel
from ...view.layouts import (
    REGION_DETAIL_BAND,
    REGION_FOOTER,
    REGION_HEADER,
    REGION_MAIN_LEFT,
    REGION_MAIN_RIGHT,
    REGION_MAIN_RIGHT_BOTTOM,
    REGION_SUMMARY,
)
from . import modules as mod


# Heights for fixed-size regions (rows).
HEADER_H = 3
SUMMARY_H = 5
FOOTER_H = 3
# Floor on the main grid (cards + chart + bottom). Below this the detail
# band stops growing; the user sees a truncation indicator instead.
MIN_MAIN_H = 14


def render_view_model(
    view: ViewModel,
    *,
    console_width: int,
    console_height: int,
) -> RenderableType:
    """Compose a Rich Layout for the given ViewModel."""
    layout_spec = view.layout
    modules = view.modules
    by_region: Dict[str, RegionSpec] = {r.region_id: r for r in layout_spec.regions}

    # ── reserve detail-band height (cells panel) ────────────────────────
    detail_h = _detail_band_height(view, console_height)
    max_data_rows = max(1, detail_h - 4) if detail_h > 0 else None

    # ── top-level rows: header / summary / main / [detail] / footer ─────
    layout = Layout()
    sections = []
    if REGION_HEADER in by_region:
        sections.append(Layout(name=REGION_HEADER, size=HEADER_H))
    if REGION_SUMMARY in by_region:
        sections.append(Layout(name=REGION_SUMMARY, size=SUMMARY_H))
    has_main = REGION_MAIN_LEFT in by_region or REGION_MAIN_RIGHT in by_region
    if has_main:
        sections.append(Layout(name="main", ratio=1))
    if REGION_DETAIL_BAND in by_region and detail_h > 0:
        sections.append(Layout(name=REGION_DETAIL_BAND, size=detail_h))
    if REGION_FOOTER in by_region:
        sections.append(Layout(name=REGION_FOOTER, size=FOOTER_H))
    layout.split_column(*sections)

    # ── header / summary / footer (single-module, full-width) ───────────
    _maybe_render_single(layout, REGION_HEADER, by_region, modules)
    _maybe_render_single(layout, REGION_SUMMARY, by_region, modules)
    _maybe_render_single(layout, REGION_FOOTER, by_region, modules)

    # ── main grid: left = cards, right = chart [+ bottom row] ───────────
    if has_main:
        left_region = by_region.get(REGION_MAIN_LEFT)
        right_region = by_region.get(REGION_MAIN_RIGHT)
        bottom_region = by_region.get(REGION_MAIN_RIGHT_BOTTOM)

        # Horizontal split between left and right
        if left_region and right_region:
            layout["main"].split_row(
                Layout(name=REGION_MAIN_LEFT, ratio=1),
                Layout(name=REGION_MAIN_RIGHT, ratio=1),
            )
        elif left_region:
            layout["main"].split_row(Layout(name=REGION_MAIN_LEFT, ratio=1))
        elif right_region:
            layout["main"].split_row(Layout(name=REGION_MAIN_RIGHT, ratio=1))

        if left_region:
            _render_region(layout["main"][REGION_MAIN_LEFT], left_region, modules)

        if right_region:
            if bottom_region:
                # Chart on top, ranking/events row below
                layout["main"][REGION_MAIN_RIGHT].split_column(
                    Layout(name="chart", ratio=2),
                    Layout(name=REGION_MAIN_RIGHT_BOTTOM, ratio=1),
                )
                chart_h = max(
                    10,
                    (console_height - HEADER_H - SUMMARY_H - FOOTER_H - detail_h - 4) // 2,
                )
                _render_region(
                    layout["main"][REGION_MAIN_RIGHT]["chart"],
                    right_region,
                    modules,
                    chart_width=max(40, console_width // 2 - 6),
                    chart_height=chart_h,
                )
                _render_region(
                    layout["main"][REGION_MAIN_RIGHT][REGION_MAIN_RIGHT_BOTTOM],
                    bottom_region,
                    modules,
                )
            else:
                # Right column is just the chart, full height
                _render_region(
                    layout["main"][REGION_MAIN_RIGHT],
                    right_region,
                    modules,
                    chart_width=max(40, console_width // 2 - 6),
                    chart_height=max(
                        10,
                        (console_height - HEADER_H - SUMMARY_H - FOOTER_H - detail_h - 4),
                    ),
                )

    # ── detail band: cells, run_metadata, etc. ──────────────────────────
    if REGION_DETAIL_BAND in by_region and detail_h > 0:
        _render_region(
            layout[REGION_DETAIL_BAND],
            by_region[REGION_DETAIL_BAND],
            modules,
            max_data_rows=max_data_rows,
        )

    return layout


def _detail_band_height(view: ViewModel, console_height: int) -> int:
    """Compute the requested-vs-available height for the detail band."""
    by_region = {r.region_id: r for r in view.layout.regions}
    region = by_region.get(REGION_DETAIL_BAND)
    if region is None:
        return 0
    requested = 0
    for mid in region.module_ids:
        spec = view.modules.get(mid)
        if spec is None:
            continue
        if spec.kind == "cells_table":
            n = len(getattr(spec, "rows", ()) or ())
            requested = max(requested, max(5, n + 4))
        elif spec.kind == "run_metadata":
            requested = max(requested, 8)
        else:
            requested = max(requested, 6)
    available = max(0, console_height - HEADER_H - SUMMARY_H - FOOTER_H - MIN_MAIN_H)
    return min(requested, available) if requested else 0


def _maybe_render_single(
    layout: Layout,
    region_id: str,
    by_region: Dict[str, RegionSpec],
    modules: Dict[str, "object"],
) -> None:
    region = by_region.get(region_id)
    if region is None or not region.module_ids:
        return
    mid = region.module_ids[0]
    spec = modules.get(mid)
    if spec is None:
        return
    layout[region_id].update(mod.render_module(spec))  # type: ignore[arg-type]


def _render_region(
    target: Layout,
    region: RegionSpec,
    modules: Dict[str, "object"],
    *,
    chart_width: int = 100,
    chart_height: int = 12,
    max_data_rows: Optional[int] = None,
) -> None:
    """Render one region's modules into the given Layout target."""
    ids = list(region.module_ids)
    if not ids:
        return

    if len(ids) == 1:
        spec = modules.get(ids[0])
        if spec is None:
            return
        target.update(
            mod.render_module(  # type: ignore[arg-type]
                spec,
                width=chart_width,
                height=chart_height,
                max_data_rows=max_data_rows,
            )
        )
        return

    # Multiple modules in this region: split horizontally or vertically
    if region.orientation == "horizontal":
        sub = [Layout(name=f"{region.region_id}_{i}", ratio=1) for i in range(len(ids))]
        target.split_row(*sub)
    else:
        sub = [Layout(name=f"{region.region_id}_{i}", ratio=1) for i in range(len(ids))]
        target.split_column(*sub)

    for i, mid in enumerate(ids):
        spec = modules.get(mid)
        if spec is None:
            continue
        target[f"{region.region_id}_{i}"].update(
            mod.render_module(  # type: ignore[arg-type]
                spec,
                width=chart_width,
                height=chart_height,
                max_data_rows=max_data_rows,
            )
        )
