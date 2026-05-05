# llama-benchy-viz-tui

Live terminal dashboard for [llama-benchy](https://github.com/eugr/llama-benchy)
benchmark runs. Consumes the `--emit-progress` JSONL stream and renders a
colorful real-time dashboard with throughput, TTFT, prefill / decode tok/s,
and live ranking across concurrent requests.

> **Status:** under development. Scaffold only — UI not yet implemented.

## Schema

This tool consumes the
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
```

Press `q`, `Esc`, or `Ctrl+C` to exit.

## Flags

- `[PATH]` — JSONL path or `-` for stdin (default).
- `--auto-exit` — exit automatically after seeing `bench_complete`.
- `--hold N` — seconds to hold the final frame on screen (default: 10).

## License

MIT — see [LICENSE](LICENSE).
