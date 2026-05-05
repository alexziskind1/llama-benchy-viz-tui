"""Aggregate dashboard state.

Maintains one `RequestState` per `request_id` plus a derived view (rolling
tok/s, ranking, summary cards). The reader thread mutates state via the
event ingest API; the UI thread reads consistent snapshots.
"""

from __future__ import annotations

# TODO:
#   - RequestState dataclass (start_ts, first_token_ts, end_ts,
#     prompt_size, response_size, gen_tokens, current_tps, avg_tps, …)
#   - AppState with .ingest(envelope), .snapshot(), thread-safe via lock
#   - derived helpers: leader_now, best_avg, fastest_ttft, ranking
