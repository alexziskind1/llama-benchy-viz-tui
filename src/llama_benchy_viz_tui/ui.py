"""Rich-based dashboard renderer.

Builds a Rich Renderable from a snapshot of `state.AppState`. The UI thread
wraps this in `rich.live.Live` and refreshes at a fixed cadence.

Layout (top → bottom):

    +-------------------------------------------------------+
    | header: title / elapsed / benchmark name / N streams  |
    +---------------+-----------------------+---------------+
    | summary cards: leader / best avg / fastest TTFT       |
    +---------------+-----------------------+---------------+
    |               |                       |               |
    | stream cards  |  hero tok/s chart     |               |
    | (2x2 grid)    |                       |               |
    |               +-----------------------+---------------+
    |               | ranking | events log                  |
    +---------------+---------+-------------------------------+
    | footer: display mode tabs                              |
    +-------------------------------------------------------+
"""

from __future__ import annotations

# TODO:
#   - render(snapshot, *, console_width, console_height) -> Renderable
#   - sub-renderers per panel
#   - per-stream color palette: pink, green, yellow/orange, purple
