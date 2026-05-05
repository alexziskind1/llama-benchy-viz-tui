#!/usr/bin/env bash
# Capture a fixture with --no-cache (unique UUID per prompt + cache_prompt=false).
# Pair with capture-sweep-pp.sh / capture-sweep-depth.sh to compare cached vs
# uncached prefill speeds across two fixtures.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/no-cache-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 \
  --tg 256 \
  --depth 4096 \
  --concurrency 1 \
  --runs 3 \
  --no-cache \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
