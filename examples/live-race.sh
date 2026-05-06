#!/usr/bin/env bash
# Run FOUR models concurrently, merge their JSONL streams, pipe into
# the live-race dashboard (4 = MAX_SLOTS). Models can share a server or
# use different OpenAI-compatible endpoints.
#
# Usage:
#   ./examples/live-race.sh
#   MODEL_A=foo MODEL_B=bar MODEL_C=baz MODEL_D=qux ./examples/live-race.sh
#
# Env knobs (with defaults):
#   MODEL_A, TOKENIZER_A, BASE_URL_A
#   MODEL_B, TOKENIZER_B, BASE_URL_B
#   MODEL_C, TOKENIZER_C, BASE_URL_C
#   MODEL_D, TOKENIZER_D, BASE_URL_D

set -euo pipefail

BENCHY=/Users/alex/Code/youtube/llama-benchy/.venv/bin/llama-benchy
VIZ=/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui
HERE=$(cd "$(dirname "$0")" && pwd)
MERGE="$HERE/_merge_benchys.py"

MODEL_A="${MODEL_A:-qwen/qwen3-4b-2507}"
TOKENIZER_A="${TOKENIZER_A:-Qwen/Qwen3-4B}"
BASE_URL_A="${BASE_URL_A:-http://localhost:1234/v1}"

MODEL_B="${MODEL_B:-qwen/qwen3-4b}"
TOKENIZER_B="${TOKENIZER_B:-${MODEL_B}}"
BASE_URL_B="${BASE_URL_B:-http://localhost:1234/v1}"

MODEL_C="${MODEL_C:-qwen2.5-3b@q8_0}"
TOKENIZER_C="${TOKENIZER_C:-${MODEL_C}}"
BASE_URL_C="${BASE_URL_C:-http://localhost:1234/v1}"

MODEL_D="${MODEL_D:-gemma-4-31b@4bit}"
TOKENIZER_D="${TOKENIZER_D:-${MODEL_D}}"
BASE_URL_D="${BASE_URL_D:-http://localhost:1234/v1}"

COMMON="--pp 512 2048 8192 --tg 128 256 4096 --runs 1 --no-warmup --skip-coherence --latency-mode none --emit-progress -"

PRODUCER_A="$BENCHY --base-url $BASE_URL_A --model $MODEL_A --tokenizer $TOKENIZER_A $COMMON"
PRODUCER_B="$BENCHY --base-url $BASE_URL_B --model $MODEL_B --tokenizer $TOKENIZER_B $COMMON"
PRODUCER_C="$BENCHY --base-url $BASE_URL_C --model $MODEL_C --tokenizer $TOKENIZER_C $COMMON"
PRODUCER_D="$BENCHY --base-url $BASE_URL_D --model $MODEL_D --tokenizer $TOKENIZER_D $COMMON"

python3 "$MERGE" \
  --producer "$PRODUCER_A" \
  --producer "$PRODUCER_B" \
  --producer "$PRODUCER_C" \
  --producer "$PRODUCER_D" \
  | "$VIZ" --mode live-race --name "race"
