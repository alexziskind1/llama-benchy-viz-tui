"""Domain layer — canonical state model + event-sourced aggregation.

This is the renderer-agnostic core: pure dataclasses, an event-sourced
store, derived metrics. **No Rich/UI dependencies.** Anything in here can
be reused by a TUI, a web dashboard, a CLI summarizer, or a test harness.

Two halves:

  state.py   — dataclasses (`SlotState`, `CellState`, `Snapshot`, …) and
               the constants that describe the shape of the state.
  store.py   — `AppState`: takes wire-format `Envelope`s in, produces
               immutable `Snapshot`s out.

The public re-exports below let consumers write a single import line:

    from llama_benchy_viz_tui.domain import AppState, Snapshot, SlotState, …
"""

from .state import (
    CHART_HISTORY_S,
    CURRENT_TPS_WINDOW_S,
    EVENT_LOG_MAX,
    HISTORY_MAX,
    MAX_SLOTS,
    SLOT_COLORS,
    SPARK_POINTS,
    CellAggregate,
    CellKey,
    CellRunResult,
    EventEntry,
    RequestState,
    SlotState,
    Snapshot,
)
from .store import AppState

__all__ = [
    "AppState",
    "CHART_HISTORY_S",
    "CURRENT_TPS_WINDOW_S",
    "CellAggregate",
    "CellKey",
    "CellRunResult",
    "EVENT_LOG_MAX",
    "EventEntry",
    "HISTORY_MAX",
    "MAX_SLOTS",
    "RequestState",
    "SLOT_COLORS",
    "SPARK_POINTS",
    "SlotState",
    "Snapshot",
]
