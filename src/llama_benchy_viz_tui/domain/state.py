"""Aggregate dashboard state.

The reader thread feeds Envelopes into ``AppState.ingest``. The UI thread
takes ``snapshot()`` once per render tick and renders from that.

Slot derivation: each unique ``(model, base_url)`` pair seen in
``request_start`` events maps to one slot (cap 4). Multiple in-flight
requests against the same target share one slot — their tokens, decode
time and ranking aggregate together.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Deque, Dict, List, Optional, Tuple

from ..ingest.schema import Envelope


# Stream colors, cycled by slot index. Match the original spec.
SLOT_COLORS: List[str] = [
    "#ff3aa1",  # 1: pink/magenta
    "#39ff7a",  # 2: bright green
    "#ffb000",  # 3: yellow/orange
    "#a96bff",  # 4: purple/violet
]

MAX_SLOTS = 4

# How wide a window (in stream-time seconds) we use for the "current tok/s"
# rolling average. Driven by event timestamps, not wall clock — so replays
# of finished JSONL files compute the same numbers as live runs.
CURRENT_TPS_WINDOW_S = 5.0

# How far back the hero chart looks (seconds).
CHART_HISTORY_S = 120.0

# Caps so long benchmarks don't accumulate unbounded state.
HISTORY_MAX = 4096
SPARK_POINTS = 32
EVENT_LOG_MAX = 60


@dataclass
class RequestState:
    """Per-request liveness data."""

    request_id: int
    start_ts: float
    first_token_ts: Optional[float] = None
    end_ts: Optional[float] = None
    prompt_size: int = 0
    response_size: int = 0
    context_size: int = 0
    concurrency: int = 0
    run_index: int = 0
    gen_tokens: int = 0
    error: str = ""
    # ttft as measured by the producer with time.perf_counter() — captured
    # off the request_first_token event so cell aggregates can use the
    # producer's accurate reading rather than wall-clock event-ts deltas.
    ttft_s: Optional[float] = None
    # ttfr (time to first response chunk) — distinct from ttft when the
    # server sends an empty role-only chunk before the first content chunk.
    ttfr_s: Optional[float] = None

    # Peak tg tok/s for this request — max tokens seen in any 1-second
    # window during decode, computed incrementally as tokens events arrive.
    # Matches llama-benchy's peak_throughput definition.
    peak_tg: float = 0.0
    _peak_window: Deque[Tuple[float, int]] = field(
        default_factory=lambda: deque(maxlen=2048)
    )

    @property
    def is_finished(self) -> bool:
        return self.end_ts is not None


@dataclass(frozen=True)
class CellKey:
    """Unique workload-cell identity within a slot.

    Each `(pp, tg, depth, concurrency)` tuple is one cell. With sweep flags
    (e.g. ``--pp 256 1024 4096``) the runner produces multiple cells per
    bench; without sweeps there's exactly one cell. Sweep panels show one
    row per cell along their axis."""

    pp: int
    tg: int
    depth: int
    concurrency: int


@dataclass
class CellRunResult:
    """One completed request's contribution to a cell's stats."""

    request_id: int
    ttft_s: Optional[float]   # e2e_ttft (first content token)
    ttfr_s: Optional[float]   # time to first response chunk (any data)
    est_ppt_s: Optional[float]  # ttfr − latency (estimated prompt processing)
    pp_tps: Optional[float]   # prompt_size / est_ppt
    tg_tps: Optional[float]   # gen_tokens / decode_seconds when known
    peak_tg: Optional[float]  # max tokens in any 1-s decode window
    total_tokens: int
    decode_seconds: float
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def has_data(self) -> bool:
        """Whether the request produced any usable timing/token data.

        A request can `ok` (no error from the producer's perspective) yet
        still have `has_data == False` if the server returned `200 OK` with
        no content — e.g. context-window overflow on some servers.
        """
        return self.total_tokens > 0 and (self.tg_tps is not None or self.pp_tps is not None)


@dataclass
class CellAggregate:
    """Running stats for one workload cell."""

    key: CellKey
    runs: List[CellRunResult] = field(default_factory=list)
    in_flight: int = 0  # currently active requests for this cell

    @property
    def completed(self) -> int:
        """Successful runs that produced data — what the dashboard means by 'a result'."""
        return sum(1 for r in self.runs if r.ok and r.has_data)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.runs if not r.ok)

    @property
    def empty(self) -> int:
        """Runs the producer reported as ok but which had zero usable tokens
        (server returned 200 with no content, context overflow, etc.)."""
        return sum(1 for r in self.runs if r.ok and not r.has_data)

    @property
    def pp_tps_mean(self) -> Optional[float]:
        vals = [r.pp_tps for r in self.runs if r.pp_tps is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def tg_tps_mean(self) -> Optional[float]:
        vals = [r.tg_tps for r in self.runs if r.tg_tps is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def ttft_s_mean(self) -> Optional[float]:
        vals = [r.ttft_s for r in self.runs if r.ttft_s is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def ttfr_s_mean(self) -> Optional[float]:
        vals = [r.ttfr_s for r in self.runs if r.ttfr_s is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def est_ppt_s_mean(self) -> Optional[float]:
        vals = [r.est_ppt_s for r in self.runs if r.est_ppt_s is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def peak_tg_mean(self) -> Optional[float]:
        vals = [r.peak_tg for r in self.runs if r.peak_tg is not None]
        return sum(vals) / len(vals) if vals else None


@dataclass
class SlotState:
    """One stream slot — typically one (model, base_url) pair."""

    slot: int
    label: str
    model: str
    base_url: str
    color: str

    # Latest configured params (from the most recent `request_start`).
    prompt_size: int = 0
    response_size: int = 0
    context_size: int = 0
    concurrency: int = 0

    # Live per-slot counters across all requests (in-flight + finished).
    total_gen_tokens: int = 0
    requests_finished: int = 0

    # Decode-time accounting.
    _active_decoders: int = 0
    _decode_started_at: Optional[float] = None
    _total_decode_seconds: float = 0.0

    # Rolling token-arrival times (event-ts). Used for current_tps.
    _token_window: Deque[Tuple[float, int]] = field(
        default_factory=lambda: deque(maxlen=4096)
    )

    # Derived metrics, recomputed on token / first-token / request_end events.
    current_tps: float = 0.0
    avg_tps: float = 0.0
    last_ttft_s: Optional[float] = None
    last_pp_tps: Optional[float] = None
    last_prompt_tokens: int = 0

    # Rolling text snippet for the OUTPUT line.
    output_snippet: str = ""

    # History points (event_ts, current_tps_at_that_time) for the hero chart.
    history: Deque[Tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_MAX)
    )
    sparkline: Deque[float] = field(
        default_factory=lambda: deque(maxlen=SPARK_POINTS)
    )

    # Per-slot phase derived from active requests.
    phase: str = "LOADING"

    # Open per-request state for in-flight requests on this slot.
    active_requests: Dict[int, RequestState] = field(default_factory=dict)
    last_error: str = ""

    # Workload cells observed on this slot, keyed by (pp, tg, depth, concurrency).
    # Populated on request_start, finalized on request_end.
    cells: Dict[CellKey, CellAggregate] = field(default_factory=dict)

    # ---- sweep-axis variation helpers ----
    @property
    def pp_values(self) -> List[int]:
        return sorted({k.pp for k in self.cells})

    @property
    def tg_values(self) -> List[int]:
        return sorted({k.tg for k in self.cells})

    @property
    def depth_values(self) -> List[int]:
        return sorted({k.depth for k in self.cells})

    @property
    def concurrency_values(self) -> List[int]:
        return sorted({k.concurrency for k in self.cells})

    @property
    def pp_varies(self) -> bool:
        return len(self.pp_values) > 1

    @property
    def tg_varies(self) -> bool:
        return len(self.tg_values) > 1

    @property
    def depth_varies(self) -> bool:
        return len(self.depth_values) > 1

    @property
    def concurrency_varies(self) -> bool:
        return len(self.concurrency_values) > 1


@dataclass
class EventEntry:
    """One line for the events panel."""

    ts: float
    slot: Optional[int]
    label: str
    text: str


@dataclass
class Snapshot:
    """Read-only view of the dashboard at one instant. UI consumes this."""

    benchmark_name: str
    started_ts: float
    last_event_ts: float
    finished: bool
    llama_benchy_version: str
    slots: List[SlotState]
    events: List[EventEntry]
    chart_y_max: float = 5.0  # ratcheted upward by AppState; chart uses as-is
    latency_s: Optional[float] = None  # measured network latency for est_ppt
    latency_mode: str = ""
    cells_scroll_offset: int = 0  # first visible cell row; clamped at render
    show_events: bool = False  # whether to render the events log panel

    @property
    def elapsed_s(self) -> float:
        if self.last_event_ts <= 0 or self.started_ts <= 0:
            return 0.0
        return max(0.0, self.last_event_ts - self.started_ts)

    @property
    def active_count(self) -> int:
        return sum(1 for s in self.slots if s.phase in ("PREFILL", "DECODE"))

    @property
    def configured_count(self) -> int:
        return len(self.slots)

    def leader_now(self) -> Optional[SlotState]:
        active = [s for s in self.slots if s.phase == "DECODE"]
        pool = active or [s for s in self.slots if s.total_gen_tokens > 0]
        if not pool:
            return None
        return max(pool, key=lambda s: s.current_tps)

    def best_avg(self) -> Optional[SlotState]:
        pool = [s for s in self.slots if s.avg_tps > 0]
        if not pool:
            return None
        return max(pool, key=lambda s: s.avg_tps)

    def fastest_ttft(self) -> Optional[SlotState]:
        pool = [s for s in self.slots if s.last_ttft_s is not None]
        if not pool:
            return None
        return min(pool, key=lambda s: s.last_ttft_s or float("inf"))

    def ranking_by_avg(self) -> List[SlotState]:
        return sorted(
            (s for s in self.slots if s.avg_tps > 0 or s.total_gen_tokens > 0),
            key=lambda s: s.avg_tps,
            reverse=True,
        )

