#!/usr/bin/env bash
# Capture a JSONL fixture sweeping --depth (context size).
# Three cells (depth=0, 4096, 16384), one run each. Useful for showing
# how prefill cost scales with context length.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/sweep-depth-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 512 \
  --tg 256 \
  --depth 0 4096 16384 \
  --concurrency 1 \
  --runs 1 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
