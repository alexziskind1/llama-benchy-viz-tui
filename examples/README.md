# Example scripts and fixtures

Capture scripts run [llama-benchy](https://github.com/eugr/llama-benchy)
against your local LM endpoint and save the `--emit-progress` JSONL stream
into `examples/fixtures/`. The fixtures are then replayable through
`llama-benchy-viz-tui` — they're how we exercise different visualizer code
paths during development without having to re-run the bench every time.

All scripts assume LM Studio (or any OpenAI-compatible server) at
`http://localhost:1234/v1` with `qwen/qwen3-4b-2507` loaded. Edit the
`--base-url` / `--model` lines if your setup differs.

## Capture scripts (one fixture per script unless noted)

| Script | What it varies | Cells × runs | tg | Tests |
|---|---|---|---|---|
| `capture-sweep-pp.sh` | `--pp 256 1024 4096` | 3 × 1 | 256 | PP sweep panel |
| `capture-sweep-tg.sh` | `--tg 256 512 1024` | 3 × 1 | varies | TG sweep panel |
| `capture-sweep-depth.sh` | `--depth 0 4096 16384` | 3 × 1 | 256 | Depth sweep panel |
| `capture-sweep-concurrency.sh` | `--concurrency 1 2 4` | 3 × 1 | 384 | Concurrency / parallel-decode handling |
| `capture-multi-runs.sh` | `--runs 5` | 1 × 5 | 256 | Run-to-run stats (mean ± std) |
| `capture-no-cache.sh` | `--no-cache` | 1 × 3 | 256 | No-cache flag (compare with a cached fixture) |
| `capture-prefix-caching.sh` | `--enable-prefix-caching` | 1 × 1 | 256 | Two-phase (context-load + inference) request stream |
| `capture-latency-modes.sh` | `--latency-mode {api,generation,none}` | 3 separate fixtures | 256 | Latency-mode comparison across invocations |
| `capture-comprehensive.sh` | pp × tg × depth × concurrency | 16 × 2 = 32 requests | 128/256 | Multiple sweep panels active at once |

Run any one of them and watch the path it prints at the end:

```bash
./examples/capture-sweep-pp.sh
# ... bench output ...
# captured: /Users/alex/.../fixtures/sweep-pp-20260505_140523.jsonl
```

## Replay a fixture in the dashboard

```bash
./examples/replay.sh fixtures/sweep-pp-*.jsonl
```

The replay wrapper sets `--auto-exit --hold 5` so it returns to the shell
shortly after `bench_complete`. Press `Ctrl+C` to skip the hold.

If you want to keep the dashboard open until you Ctrl+C (no auto-exit),
just call viz-tui directly:

```bash
/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui fixtures/sweep-pp-*.jsonl
```

(Without `--auto-exit`, viz-tui stays on screen forever — the previous
"exit ~10s after bench_complete" behavior was a bug, now fixed.)

## Run everything at once

```bash
./examples/run-all-captures.sh
```

Runs each capture script in sequence, printing a banner before each.
Takes a few minutes against a local model; produces one fixture per
script in `fixtures/`.

## Live (no fixture)

If you'd rather pipe a fresh bench straight into the dashboard with no
saved file:

```bash
./examples/live-qwen3-4b-2507.sh
```

This is the original demo script; it pipes `--emit-progress -` directly
into the viz-tui binary.

## Notes

- Fixtures are git-ignored (`*.jsonl` matches them). Safe to keep around.
- Scripts assume the venvs at:
  - `/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy`
  - `/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui`
  Edit the path constants at the top of each script if yours differ.
