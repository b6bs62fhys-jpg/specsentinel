#!/usr/bin/env bash
# Example 1: a simple run.
# Checks the demo API against examples/petstore.yaml, first the conforming
# variant (exit code 0), then the drifting one (exit code 1).
set -u
cd "$(dirname "$0")/.."
. examples/_demo.sh

start_demo "$PORT"
start_demo "$((PORT + 1))" --conform

show specsentinel examples/petstore.yaml --url "http://127.0.0.1:$((PORT + 1))"
show specsentinel examples/petstore.yaml --url "http://127.0.0.1:$PORT"
exit "$last_code"
