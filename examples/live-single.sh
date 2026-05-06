#!/usr/bin/env bash
# Pipe a single-model llama-benchy run straight into the dashboard.
# Auto-detects "live-single" mode (1 stream, in-flight).
#
# Usage:
#   ./examples/live-single.sh
#   MODEL=foo TOKENIZER=bar BASE_URL=http://h:1234/v1 ./examples/live-single.sh

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
VIZ=/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui

MODEL="${MODEL:-qwen/qwen3-4b-2507}"
TOKENIZER="${TOKENIZER:-Qwen/Qwen3-4B}"
BASE_URL="${BASE_URL:-http://localhost:1234/v1}"

"$BENCHY" \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --tokenizer "$TOKENIZER" \
  --pp 16 32 64 128 256 512 1024 2048 \
  --tg 16 32 64 128 256  \
  --runs 1 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress - \
  | "$VIZ" --name "$MODEL · live"
