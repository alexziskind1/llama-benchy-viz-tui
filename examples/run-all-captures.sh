#!/usr/bin/env bash
# Run every capture-*.sh in sequence to produce a full set of fixtures.
# Total wall clock: ~3-5 minutes against a local model.

set -euo pipefail

DIR=$(cd "$(dirname "$0")" && pwd)

scripts=(
  capture-sweep-pp.sh
  capture-sweep-tg.sh
  capture-sweep-depth.sh
  capture-sweep-concurrency.sh
  capture-multi-runs.sh
  capture-no-cache.sh
  capture-prefix-caching.sh
  capture-latency-modes.sh
  capture-comprehensive.sh
)

for s in "${scripts[@]}"; do
  echo
  echo "============================================================"
  echo "  $s"
  echo "============================================================"
  "$DIR/$s"
done

echo
echo "all captures done. fixtures in $DIR/fixtures/"
ls -1t "$DIR/fixtures/" | head -20
