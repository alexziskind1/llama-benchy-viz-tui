# llama-benchy-viz-tui

Live terminal dashboard for [llama-benchy](https://github.com/eugr/llama-benchy)
benchmark runs. Consumes the `--emit-progress` JSONL stream and renders a
colorful real-time dashboard with throughput, TTFT, prefill / decode tok/s,
and (when comparing models) a live ranking.

The dashboard auto-adapts to four distinct modes:

|             | one model      | 2-4 models       |
|-------------|----------------|------------------|
| **live**    | `live-single`  | `live-race`      |
| **static**  | `static-single`| `static-race`    |

Auto-detected from the JSONL stream. Override with `--mode`.

## Schema

Consumes the
[`llama-benchy-progress.v1`](https://github.com/eugr/llama-benchy/blob/main/docs/progress-schema.md)
JSONL stream produced by `llama-benchy --emit-progress`.

## Install

Using `uv` (recommended):

```bash
uv venv
uv pip install -e .
source .venv/bin/activate
```

Or with `pip`:

```bash
python -m venv .venv
.venv/bin/pip install -e .
source .venv/bin/activate
```

## Use

```bash
# Tail-follow a JSONL file written by llama-benchy --emit-progress PATH
llama-benchy-viz-tui /tmp/progress.jsonl

# Pipe straight from a live benchmark
llama-benchy --emit-progress - --base-url http://localhost:1234/v1 --model … \
  | llama-benchy-viz-tui

# Replay a finished JSONL fixture
llama-benchy-viz-tui --auto-exit /tmp/progress.jsonl

# Force a specific mode (e.g. for screen recordings)
llama-benchy-viz-tui --mode live-race /tmp/progress.jsonl
```

Press `q`, `Esc`, or `Ctrl+C` to exit. Inside the dashboard:
`↑/↓/j/k` scroll the cells panel one row, `PgUp/PgDn` page, `g/G` jump
to top/bottom.

## What each mode shows

- **live-single** — progress-first. Big stream card, live tok/s chart
  on the right, cells table populating below as the sweep progresses.
- **live-race** (≥2 models, in flight) — visually rich. 2x2 stream
  cards on the left, live comparison chart on the right with a ranking
  + events row beneath it.
- **static-single** — focused post-run summary. Final stream card +
  full-history chart + complete cells table + run metadata.
- **static-race** — comparison-first. Frozen stream grid + final
  comparison chart + final ranking + per-run metadata.

## Flags

- `[PATH]` — JSONL path or `-` / omitted for stdin.
- `--mode {static-single,static-race,live-single,live-race}` — override
  the auto-detected mode.
- `--auto-exit` — exit automatically `--hold N` seconds after
  `bench_complete`. Without this flag the dashboard stays on screen
  until `Ctrl+C`.
- `--hold N` — with `--auto-exit`: seconds to hold the final frame
  (default: 10).
- `--name NAME` — header label (default: `benchmark`).
- `--fps HZ` — render frame-rate cap (default: 8).
- `--show-events` — show the rolling events panel even when
  uninteresting. Off by default.

## Architecture

This package is layered so a future web or native renderer can plug
into the same ViewModel layer the TUI uses. See [DESIGN.md](DESIGN.md)
for the full layered architecture, module catalog, and instructions
for adding new renderers / modes / modules.

```
ingest/   ← JSONL + schema parsing
domain/   ← state model + event-sourced store (no UI imports)
view/     ← ModuleSpec / LayoutSpec / DashboardMode / compose
renderer/ ← Rich-based TUI (one of N possible frontends)
ui.py     ← thin façade: Snapshot → ViewModel → Rich Layout
```

## License

MIT — see [LICENSE](LICENSE).
