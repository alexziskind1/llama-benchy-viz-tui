#!/usr/bin/env bash
# Capture a JSONL fixture sweeping --concurrency.
# Three levels (1, 2, 4), one run each. Useful for testing how the
# visualizer handles parallel requests with overlapping decode segments.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/sweep-concurrency-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 \
  --tg 384 \
  --depth 0 \
  --concurrency 1 2 4 \
  --runs 1 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
