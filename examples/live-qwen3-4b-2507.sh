#!/usr/bin/env bash
# Pipe a fresh llama-benchy run straight into the viz-tui dashboard.
# Edit the BENCHY / VIZ paths and target args for your setup.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
VIZ=/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 2048 8192 16000 --tg 64 128 256 512 1024 --runs 1 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress - \
  | "$VIZ" --name "qwen3-4b-2507 live"
