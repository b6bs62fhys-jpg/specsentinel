#!/usr/bin/env bash
# Example 2: adopt SpecSentinel with a baseline.
# 1. Record the drift the API has today in a baseline file (exit code 0).
# 2. Check again with the baseline: known drift no longer fails (exit code 0).
#    Only new drift would fail the run.
set -u
cd "$(dirname "$0")/.."
. examples/_demo.sh
WORKDIR="${WORKDIR:-$(mktemp -d)}"
BASELINE="$WORKDIR/specsentinel-baseline.json"

start_demo "$PORT"

show specsentinel examples/petstore.yaml --url "http://127.0.0.1:$PORT" --write-baseline "$BASELINE"
echo "Baseline written to $BASELINE"
echo
show specsentinel examples/petstore.yaml --url "http://127.0.0.1:$PORT" --baseline "$BASELINE"
exit "$last_code"
