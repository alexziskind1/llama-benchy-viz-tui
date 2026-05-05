#!/usr/bin/env bash
# Capture a fixture with --runs 5 — five sequential runs of one cell.
# Useful for testing run-stability stats (mean ± std, run-to-run variance).

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$DIR/fixtures/multi-runs-${TS}.jsonl"

"$BENCHY" \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3-4b-2507 \
  --tokenizer Qwen/Qwen3-4B \
  --pp 1024 \
  --tg 256 \
  --depth 0 \
  --concurrency 1 \
  --runs 5 \
  --no-warmup --skip-coherence --latency-mode none \
  --emit-progress "$OUT"

echo
echo "captured: $OUT"
