#!/usr/bin/env bash
# Capture a fixture with --enable-prefix-caching. The runner adds an extra
# "context-load" phase before each inference run that warms the prefix cache,
# so the JSONL contains roughly 2x the requests of a normal run.
# Note: v1 schema doesn't tag the phase explicitly — the visualizer must
# infer it from the request_start parameters (context-load has prompt_text="").

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/prefix-caching-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 \
  --tg 256 \
  --depth 4096 \
  --concurrency 1 \
  --runs 1 \
  --enable-prefix-caching \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
