#!/usr/bin/env bash
# Capture a JSONL fixture sweeping --tg (token generation counts).
# Three cells (tg=32, 128, 512), one run each. Useful for testing the
# TG-sweep panel of the visualizer.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/sweep-tg-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 \
  --tg 256 512 1024 \
  --depth 0 \
  --concurrency 1 \
  --runs 1 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
