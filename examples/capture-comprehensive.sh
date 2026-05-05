#!/usr/bin/env bash
# Comprehensive sweep — exercises pp × tg × depth × concurrency in one run,
# with --runs 2 for stability. Useful for stress-testing the visualizer's
# layout (multiple sweep panels active simultaneously) and the cell
# aggregation path.
#
# Cell count: 2 × 2 × 2 × 2 = 16 cells × 2 runs = 32 requests.
# Wall clock: ~60-90s on a fast local model.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/comprehensive-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 512 2048 \
  --tg 128 256 \
  --depth 0 4096 \
  --concurrency 1 2 \
  --runs 2 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
