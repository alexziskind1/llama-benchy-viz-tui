"""DashboardMode — picks the dashboard "shape" from the snapshot.

Four modes, two axes:

    static_single ─┐                ┌─ live_single
                   ├─ "race" axis ──┤
    static_race ───┘                └─ live_race

The ``Live ↔ Static`` axis is decided by ``snapshot.finished``: anything
that's still streaming is live; once ``bench_complete`` has arrived, it's
static. The ``Single ↔ Race`` axis is decided by the number of distinct
``(model, base_url)`` slots: 1 → single, ≥2 → race.

Auto-detection is the default. ``--mode`` on the CLI overrides for cases
where the user wants the race look on a single-stream replay (or vice
versa) for a screen recording or comparison shot.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from ..domain import Snapshot


class DashboardMode(str, Enum):
    STATIC_SINGLE = "static-single"
    STATIC_RACE = "static-race"
    LIVE_SINGLE = "live-single"
    LIVE_RACE = "live-race"

    @property
    def is_live(self) -> bool:
        return self in (DashboardMode.LIVE_SINGLE, DashboardMode.LIVE_RACE)

    @property
    def is_race(self) -> bool:
        return self in (DashboardMode.STATIC_RACE, DashboardMode.LIVE_RACE)


def detect(snap: Snapshot) -> DashboardMode:
    """Auto-detect the dashboard mode from current snapshot state."""
    n_slots = len(snap.slots)
    is_race = n_slots >= 2
    is_static = snap.finished
    if is_static and is_race:
        return DashboardMode.STATIC_RACE
    if is_static:
        return DashboardMode.STATIC_SINGLE
    if is_race:
        return DashboardMode.LIVE_RACE
    return DashboardMode.LIVE_SINGLE


def parse(name: Optional[str]) -> Optional[DashboardMode]:
    """Parse a CLI ``--mode`` value. Returns None for missing/empty input."""
    if name is None or not name.strip():
        return None
    candidate = name.strip().lower().replace("_", "-")
    for m in DashboardMode:
        if m.value == candidate:
            return m
    raise ValueError(
        f"Unknown dashboard mode: {name!r}. "
        f"Expected one of: {', '.join(m.value for m in DashboardMode)}"
    )
