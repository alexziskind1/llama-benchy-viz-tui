"""Event-sourced store: ingests Envelopes, exposes immutable Snapshots.

The reader thread feeds parsed Envelopes into ``AppState.ingest``; the UI
thread takes ``snapshot()`` once per render tick and renders from that.

Slot derivation: each unique ``(model, base_url)`` pair seen in
``request_start`` events maps to one slot (cap 4). Multiple in-flight
requests against the same target share one slot — their tokens, decode
time and ranking aggregate together.
"""

from __future__ import annotations

import time
from collections import deque
from threading import RLock
from typing import Deque, Dict, Optional, Tuple

from ..ingest.schema import Envelope
from .state import (
    CURRENT_TPS_WINDOW_S,
    EVENT_LOG_MAX,
    MAX_SLOTS,
    SLOT_COLORS,
    CellAggregate,
    CellKey,
    CellRunResult,
    EventEntry,
    RequestState,
    SlotState,
    Snapshot,
)


class AppState:
    """Mutable dashboard state, fed by `ingest(envelope)` from a reader thread."""

    def __init__(
        self, benchmark_name: str = "benchmark", *, show_events: bool = False
    ) -> None:
        self.benchmark_name = benchmark_name
        self.show_events = show_events
        self.started_ts: float = 0.0
        self.last_event_ts: float = 0.0
        self.finished: bool = False
        self.llama_benchy_version: str = ""
        self._slots: Dict[int, SlotState] = {}
        self._slot_for_target: Dict[Tuple[str, str], int] = {}
        self._request_to_slot: Dict[int, int] = {}
        self._request_to_cell: Dict[int, CellKey] = {}
        self._events: Deque[EventEntry] = deque(maxlen=EVENT_LOG_MAX)
        self._chart_y_max: float = 5.0  # ratcheted upward as values grow
        self._latency_s: Optional[float] = None  # measured by upstream once
        self._latency_mode: str = ""
        self._cells_scroll_offset: int = 0  # cells panel scroll position
        self._lock = RLock()

    # Cells-panel scroll API. Render-time clamping keeps callers simple —
    # they don't need to know how many rows are visible or total.
    def scroll_cells(self, delta: int) -> None:
        with self._lock:
            self._cells_scroll_offset = max(0, self._cells_scroll_offset + delta)

    def scroll_cells_home(self) -> None:
        with self._lock:
            self._cells_scroll_offset = 0

    def scroll_cells_end(self) -> None:
        with self._lock:
            # A large sentinel; cells.render clamps to actual max.
            self._cells_scroll_offset = 1_000_000

    # ingest entry point
    def ingest(self, env: Envelope) -> None:
        if not env.is_known_kind:
            return
        with self._lock:
            self.last_event_ts = max(self.last_event_ts, env.ts)
            if self.started_ts == 0.0:
                self.started_ts = env.ts

            if env.kind == "header":
                self._on_header(env)
            elif env.kind == "request_start":
                self._on_request_start(env)
            elif env.kind == "request_first_response":
                self._on_first_response(env)
            elif env.kind == "request_first_token":
                self._on_first_token(env)
            elif env.kind == "tokens":
                self._on_tokens(env)
            elif env.kind == "request_end":
                self._on_request_end(env)
            elif env.kind == "bench_complete":
                self._on_bench_complete(env)
            elif env.kind == "latency_measured":
                self._on_latency_measured(env)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(
                benchmark_name=self.benchmark_name,
                started_ts=self.started_ts,
                last_event_ts=self.last_event_ts,
                finished=self.finished,
                llama_benchy_version=self.llama_benchy_version,
                slots=[self._slots[k] for k in sorted(self._slots)],
                events=list(self._events),
                chart_y_max=self._chart_y_max,
                latency_s=self._latency_s,
                latency_mode=self._latency_mode,
                cells_scroll_offset=self._cells_scroll_offset,
                show_events=self.show_events,
            )

    # ----- handlers -----
    def _on_header(self, env: Envelope) -> None:
        self.llama_benchy_version = env.llama_benchy_version
        self._log(None, "[SYSTEM]", f"connected (llama-benchy {env.llama_benchy_version or 'unknown'})")

    def _on_request_start(self, env: Envelope) -> None:
        if env.request_id is None:
            return
        slot = self._slot_for(env.model, env.base_url)
        if slot is None:
            return
        self._request_to_slot[env.request_id] = slot.slot

        rs = RequestState(
            request_id=env.request_id,
            start_ts=env.ts,
            prompt_size=env.prompt_size,
            response_size=env.response_size,
            context_size=env.context_size,
            concurrency=env.concurrency,
            run_index=env.run_index,
        )
        slot.active_requests[env.request_id] = rs
        slot.prompt_size = env.prompt_size or slot.prompt_size
        slot.response_size = env.response_size or slot.response_size
        slot.context_size = env.context_size or slot.context_size
        slot.concurrency = env.concurrency or slot.concurrency
        if slot.phase != "DECODE":
            slot.phase = "PREFILL"

        # Register this request against its workload cell.
        ck = CellKey(
            pp=env.prompt_size,
            tg=env.response_size,
            depth=env.context_size,
            concurrency=env.concurrency or 1,
        )
        cell = slot.cells.get(ck)
        if cell is None:
            cell = CellAggregate(key=ck)
            slot.cells[ck] = cell
            self._log(
                slot.slot,
                f"[{slot.label}]",
                f"new cell pp={ck.pp} tg={ck.tg} d={ck.depth} c={ck.concurrency}",
            )
        cell.in_flight += 1
        self._request_to_cell[env.request_id] = ck

        self._log(
            slot.slot,
            f"[{slot.label}]",
            f"request {env.request_id}: pp={env.prompt_size} tg={env.response_size} d={env.context_size} run {env.run_index}",
        )

    def _on_first_response(self, env: Envelope) -> None:
        slot = self._slot_for_request(env.request_id)
        if slot is None or env.request_id is None:
            return
        rs = slot.active_requests.get(env.request_id)
        if rs is None:
            return
        rs.ttfr_s = env.ttfr_s

    def _on_latency_measured(self, env: Envelope) -> None:
        if env.latency_s is not None:
            self._latency_s = env.latency_s
        if env.mode:
            self._latency_mode = env.mode
        self._log(
            None,
            "[SYSTEM]",
            f"latency: {(env.latency_s or 0.0) * 1000:.2f} ms ({env.mode or 'unknown'})",
        )

    def _on_first_token(self, env: Envelope) -> None:
        slot = self._slot_for_request(env.request_id)
        if slot is None or env.request_id is None:
            return
        rs = slot.active_requests.get(env.request_id)
        if rs is None:
            return
        rs.first_token_ts = env.ts
        rs.ttft_s = env.ttft_s
        if env.ttft_s is not None:
            slot.last_ttft_s = env.ttft_s
            if rs.prompt_size > 0 and env.ttft_s > 0:
                slot.last_pp_tps = rs.prompt_size / env.ttft_s
                slot.last_prompt_tokens = rs.prompt_size

        if slot._active_decoders == 0:
            slot._decode_started_at = env.ts
        slot._active_decoders += 1
        slot.phase = "DECODE"
        self._recompute_avg(slot)

    def _on_tokens(self, env: Envelope) -> None:
        if env.count <= 0 and not env.snippet:
            return
        slot = self._slot_for_request(env.request_id)
        if slot is None or env.request_id is None:
            return
        rs = slot.active_requests.get(env.request_id)
        if rs is None:
            return

        slot._token_window.append((env.ts, env.count))
        rs.gen_tokens += env.count
        slot.total_gen_tokens += env.count

        # current_tps: rolling window over event-time
        cutoff = env.ts - CURRENT_TPS_WINDOW_S
        while slot._token_window and slot._token_window[0][0] < cutoff:
            slot._token_window.popleft()
        window_count = sum(c for _, c in slot._token_window)
        window_span = max(0.001, env.ts - slot._token_window[0][0]) if slot._token_window else 1.0
        slot.current_tps = window_count / max(window_span, 1.0)

        # Per-request peak_tg: max tokens-per-second in any 1-s window during
        # this request's decode. Matches llama-benchy's peak_throughput.
        rs._peak_window.append((env.ts, env.count))
        peak_cutoff = env.ts - 1.0
        while rs._peak_window and rs._peak_window[0][0] < peak_cutoff:
            rs._peak_window.popleft()
        peak_window_count = float(sum(c for _, c in rs._peak_window))
        if peak_window_count > rs.peak_tg:
            rs.peak_tg = peak_window_count

        # snippet (rolling, capped)
        if env.snippet:
            slot.output_snippet = (slot.output_snippet + env.snippet)[-280:]

        # history + sparkline
        slot.history.append((env.ts, slot.current_tps))
        slot.sparkline.append(slot.current_tps)

        # Ratchet the chart's y-axis upward only — this prevents the y-axis
        # scale from constantly recomputing and visually jumping the line.
        if slot.current_tps > self._chart_y_max:
            self._chart_y_max = slot.current_tps

        self._recompute_avg(slot, now_ts=env.ts)

    def _on_request_end(self, env: Envelope) -> None:
        slot = self._slot_for_request(env.request_id)
        if slot is None or env.request_id is None:
            return
        rs = slot.active_requests.pop(env.request_id, None)
        if rs is None:
            return
        rs.end_ts = env.ts
        rs.error = env.error
        slot.requests_finished += 1
        if env.error:
            slot.last_error = env.error

        # Finalize this request's contribution to its cell.
        ck = self._request_to_cell.pop(env.request_id, None)
        if ck is not None:
            cell = slot.cells.get(ck)
            if cell is not None:
                if cell.in_flight > 0:
                    cell.in_flight -= 1
                # Prefer the producer's perf_counter ttft_s if it was emitted;
                # fall back to the wall-clock delta between the start and
                # first-token events.
                if rs.ttft_s is not None:
                    ttft = rs.ttft_s
                elif rs.first_token_ts is not None:
                    ttft = rs.first_token_ts - rs.start_ts
                else:
                    ttft = None
                ttfr = rs.ttfr_s
                # est_ppt = ttfr − latency (canonical); fall back to ttft if
                # the producer didn't emit a separate ttfr (older fixture).
                if ttfr is not None:
                    est_ppt = max(0.0, ttfr - (self._latency_s or 0.0))
                elif ttft is not None:
                    est_ppt = max(0.0, ttft - (self._latency_s or 0.0))
                else:
                    est_ppt = None
                # pp_tps uses est_ppt to match llama-benchy's canonical formula.
                pp_tps = (
                    env.prompt_tokens / est_ppt
                    if (est_ppt and est_ppt > 0 and env.prompt_tokens > 0)
                    else None
                )
                # Match llama-benchy's canonical tg formula: the first token
                # is accounted to TTFT (prefill), not decode, so subtract one.
                tg_tps = (
                    (env.total_tokens - 1) / env.decode_seconds
                    if (env.decode_seconds > 0 and env.total_tokens > 1)
                    else None
                )
                cell.runs.append(
                    CellRunResult(
                        request_id=env.request_id,
                        ttft_s=ttft,
                        ttfr_s=ttfr,
                        est_ppt_s=est_ppt,
                        pp_tps=pp_tps,
                        tg_tps=tg_tps,
                        peak_tg=rs.peak_tg if rs.peak_tg > 0 else None,
                        total_tokens=env.total_tokens,
                        decode_seconds=env.decode_seconds,
                        error=env.error,
                    )
                )

        # Close decode segment if last decoder.
        if slot._active_decoders > 0:
            slot._active_decoders -= 1
        if slot._active_decoders == 0 and slot._decode_started_at is not None:
            slot._total_decode_seconds += env.ts - slot._decode_started_at
            slot._decode_started_at = None

        # Phase: another active = stay DECODE (or PREFILL if none have first
        # token yet); none = DONE / ERROR.
        if slot.active_requests:
            if any(r.first_token_ts is not None for r in slot.active_requests.values()):
                slot.phase = "DECODE"
            else:
                slot.phase = "PREFILL"
        else:
            slot.phase = "ERROR" if env.error else "DONE"

        self._recompute_avg(slot, now_ts=env.ts)
        self._log(
            slot.slot,
            f"[{slot.label}]",
            f"request {env.request_id} done: {env.total_tokens} toks in {env.decode_seconds:.2f}s"
            + (f" — {env.error}" if env.error else ""),
        )

    def _on_bench_complete(self, env: Envelope) -> None:
        self.finished = True
        for slot in self._slots.values():
            if slot._active_decoders > 0 and slot._decode_started_at is not None:
                slot._total_decode_seconds += env.ts - slot._decode_started_at
                slot._decode_started_at = None
                slot._active_decoders = 0
            if slot.phase not in ("DONE", "ERROR"):
                slot.phase = "DONE"
            self._recompute_avg(slot, now_ts=env.ts)
        self._log(None, "[SYSTEM]", "bench_complete — final values frozen")

    # ----- helpers -----
    def _slot_for(self, model: str, base_url: str) -> Optional[SlotState]:
        key = (model, base_url)
        if key in self._slot_for_target:
            return self._slots[self._slot_for_target[key]]
        if len(self._slots) >= MAX_SLOTS:
            # Out of slots — log once and ignore further new targets.
            return None
        slot_idx = len(self._slots)
        label = (model.split("/")[-1] if "/" in model else model) or f"slot {slot_idx + 1}"
        slot = SlotState(
            slot=slot_idx,
            label=label,
            model=model,
            base_url=base_url,
            color=SLOT_COLORS[slot_idx % len(SLOT_COLORS)],
        )
        self._slots[slot_idx] = slot
        self._slot_for_target[key] = slot_idx
        self._log(slot_idx, "[SYSTEM]", f"slot {slot_idx + 1} → {label}")
        return slot

    def _slot_for_request(self, request_id: Optional[int]) -> Optional[SlotState]:
        if request_id is None:
            return None
        slot_idx = self._request_to_slot.get(request_id)
        if slot_idx is None:
            return None
        return self._slots.get(slot_idx)

    def _recompute_avg(self, slot: SlotState, now_ts: Optional[float] = None) -> None:
        active_seconds = slot._total_decode_seconds
        if slot._decode_started_at is not None:
            ref = now_ts if now_ts is not None else self.last_event_ts
            if ref > slot._decode_started_at:
                active_seconds += ref - slot._decode_started_at
        if active_seconds > 0.001:
            slot.avg_tps = slot.total_gen_tokens / active_seconds

    def _log(self, slot: Optional[int], label: str, text: str) -> None:
        # _events is bounded; deque rotates oldest out automatically.
        self._events.append(EventEntry(ts=time.time(), slot=slot, label=label, text=text))
