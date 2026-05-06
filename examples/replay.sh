#!/usr/bin/env bash
# Replay a captured JSONL fixture in the viz-tui dashboard.
#
# Usage:
#     ./replay.sh fixtures/sweep-pp-20260505_*.jsonl
#     ./replay.sh fixtures/comprehensive-20260505_*.jsonl
#
# Auto-exits 5 seconds after bench_complete. Press Ctrl+C to skip the hold.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <fixture.jsonl> [--name LABEL]" >&2
  exit 1
fi

VIZ=/Users/alex/Code/youtube/llama-benchy-viz-tui/.venv/bin/llama-benchy-viz-tui
FIXTURE="$1"
shift

NAME=$(basename "$FIXTURE" .jsonl)

"$VIZ" --auto-exit --hold 5 --name "$NAME" "$@" "$FIXTURE"
