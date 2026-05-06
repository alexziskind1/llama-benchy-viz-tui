#!/usr/bin/env bash
# Latency mode is single-valued; comparing requires three llama-benchy runs.
# This script runs all three (--latency-mode api, generation, none) and
# captures one JSONL per mode. Use them as separate fixtures or concatenate
# them to feed the visualizer's multi-experiment ingest path.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/fixtures"
TS=$(date +%Y%m%d_%H%M%S)

for MODE in api generation none; do
  OUT="$DIR/fixtures/latency-${MODE}-${TS}.jsonl"
  echo "=== latency-mode=$MODE → $OUT ==="
  "$BENCHY" \
    --base-url http://localhost:1234/v1 \
    --model qwen/qwen3-4b-2507 \
    --tokenizer Qwen/Qwen3-4B \
    --pp 1024 --tg 256 --depth 0 --concurrency 1 --runs 1 \
    --no-warmup --skip-coherence \
    --latency-mode "$MODE" \
    --emit-progress "$OUT"
done

echo
echo "captured 3 fixtures in $DIR/fixtures/ (latency-{api,generation,none}-${TS}.jsonl)"
