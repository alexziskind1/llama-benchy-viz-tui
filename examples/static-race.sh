#!/usr/bin/env bash
# Run TWO models concurrently, capture merged JSONL to fixtures/, then
# replay through the dashboard (auto-detects "static-race" from the
# saved bench_complete + 2-stream history).
#
# Pass --watch to also pipe the live merge into the dashboard while
# capturing; the saved file can later be replayed any time.

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
VIZ=/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui
HERE=$(cd "$(dirname "$0")" && pwd)
MERGE="$HERE/_merge_benchys.py"
mkdir -p "$HERE/fixtures"

WATCH=0
if [[ "${1:-}" == "--watch" ]]; then
  WATCH=1
fi

MODEL_A="${MODEL_A:-qwen/qwen3-4b-2507}"
TOKENIZER_A="${TOKENIZER_A:-Qwen/Qwen3-4B}"
BASE_URL_A="${BASE_URL_A:-http://localhost:1234/v1}"

MODEL_B="${MODEL_B:-google/gemma-3-4b-it}"
TOKENIZER_B="${TOKENIZER_B:-${MODEL_B}}"
BASE_URL_B="${BASE_URL_B:-http://localhost:1234/v1}"

COMMON="--pp 512 2048 --tg 128 256 --runs 1 --no-warmup --skip-coherence --latency-mode none --emit-progress -"

PRODUCER_A="$BENCHY --base-url $BASE_URL_A --model $MODEL_A --tokenizer $TOKENIZER_A $COMMON"
PRODUCER_B="$BENCHY --base-url $BASE_URL_B --model $MODEL_B --tokenizer $TOKENIZER_B $COMMON"

TS=$(date +%Y%m%d_%H%M%S)
OUT="$HERE/fixtures/race-${TS}.jsonl"

if [[ $WATCH -eq 1 ]]; then
  python3 "$MERGE" --producer "$PRODUCER_A" --producer "$PRODUCER_B" \
    | tee "$OUT" \
    | "$VIZ" --mode live-race --name "race-${TS}"
  echo
  echo "captured: $OUT"
else
  python3 "$MERGE" --producer "$PRODUCER_A" --producer "$PRODUCER_B" > "$OUT"
  echo "captured: $OUT"
  echo "replaying through dashboard (Ctrl+C to exit)…"
  echo
  "$VIZ" --name "race-${TS}" "$OUT"
fi
