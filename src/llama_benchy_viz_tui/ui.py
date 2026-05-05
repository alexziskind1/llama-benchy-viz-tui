"""Layout composer.

Walks the panel modules, asks each whether it's active for the current
snapshot, and assembles a Rich `Layout`. Always-on panels (header, summary,
streams_grid, live_chart, ranking, events, footer) form the base layout.
The sweep panels (pp, tg, depth, concurrency) appear in a row above the
footer when their axis varies — and only then.
"""

from __future__ import annotations

from typing import List

from rich.console import RenderableType
from rich.layout import Layout

from . import panels
from .domain import Snapshot

# Heights of fixed-size regions (in rows).
HEADER_H = 3
SUMMARY_H = 5
FOOTER_H = 3
# Floor on what the main grid (stream cards + chart + ranking + events) gets.
# Below this, the detail panels stop growing — main always stays usable.
MIN_MAIN_H = 14


# Conditional bottom-row panels, in display order. Each module exports
# is_active(snap), render(snap), and optionally min_height(snap).
DETAIL_PANELS = (panels.cells,)


def render(snap: Snapshot, *, console_width: int, console_height: int) -> RenderableType:
    layout = Layout()

    # Decide which detail panels are active this frame and how much height
    # they want — capped at whatever the terminal can spare while keeping
    # the main grid above MIN_MAIN_H.
    active_details = [p for p in DETAIL_PANELS if p.is_active(snap)]
    requested_h = 0
    for p in active_details:
        h = getattr(p, "min_height", None)
        requested_h = max(requested_h, h(snap) if callable(h) else 8)
    available_h = max(
        0, console_height - HEADER_H - SUMMARY_H - FOOTER_H - MIN_MAIN_H
    )
    detail_h = min(requested_h, available_h) if active_details else 0
    # `max_data_rows` for the cells panel = detail_h minus its own border
    # + title + column-header overhead.
    max_data_rows = max(1, detail_h - 4) if detail_h > 0 else None

    # Top-level rows: header, summary, main, [detail panels], footer.
    sections = [
        Layout(name="header", size=HEADER_H),
        Layout(name="summary", size=SUMMARY_H),
        Layout(name="main", ratio=1),
    ]
    if active_details:
        sections.append(Layout(name="details", size=detail_h))
    sections.append(Layout(name="footer", size=FOOTER_H))
    layout.split_column(*sections)

    layout["main"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )

    ranking_active = panels.ranking.is_active(snap)
    events_active = panels.events.is_active(snap)
    has_bottom = ranking_active or events_active

    if has_bottom:
        # Chart on top, ranking/events row below.
        layout["main"]["right"].split_column(
            Layout(name="chart", ratio=2),
            Layout(name="bottom", ratio=1),
        )
        if ranking_active and events_active:
            layout["main"]["right"]["bottom"].split_row(
                Layout(name="ranking", ratio=1),
                Layout(name="events", ratio=1),
            )
        chart_layout = layout["main"]["right"]["chart"]
    else:
        # Nothing below the chart — let the chart take the full right column
        # so we don't leave an empty placeholder.
        chart_layout = layout["main"]["right"]

    # Always-on panels.
    layout["header"].update(panels.header.render(snap))
    layout["summary"].update(panels.summary.render(snap))
    layout["main"]["left"].update(panels.streams_grid.render(snap))

    chart_width = max(40, console_width // 2 - 6)
    chart_height = max(
        10,
        (console_height - HEADER_H - SUMMARY_H - FOOTER_H - detail_h - 4) // 2,
    )
    chart_layout.update(
        panels.live_chart.render(snap, width=chart_width, height=chart_height)
    )
    if has_bottom:
        if ranking_active and events_active:
            layout["main"]["right"]["bottom"]["ranking"].update(panels.ranking.render(snap))
            layout["main"]["right"]["bottom"]["events"].update(panels.events.render(snap))
        elif ranking_active:
            layout["main"]["right"]["bottom"].update(panels.ranking.render(snap))
        elif events_active:
            layout["main"]["right"]["bottom"].update(panels.events.render(snap))

    # Detail panel row (only when any are active).
    if active_details:
        # Pass `max_data_rows` to panels that accept it (cells.render does).
        def _call_panel(p):
            try:
                return p.render(snap, max_data_rows=max_data_rows)
            except TypeError:
                return p.render(snap)

        if len(active_details) == 1:
            layout["details"].update(_call_panel(active_details[0]))
        else:
            sub_columns: List[Layout] = []
            for i, _ in enumerate(active_details):
                sub_columns.append(Layout(name=f"detail_{i}", ratio=1))
            layout["details"].split_row(*sub_columns)
            for i, panel in enumerate(active_details):
                layout["details"][f"detail_{i}"].update(_call_panel(panel))

    layout["footer"].update(panels.footer.render(snap))
    return layout
