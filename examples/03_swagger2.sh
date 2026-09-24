#!/usr/bin/env bash
# Example 3: a Swagger 2.0 source.
# examples/swagger2.yaml describes the same demo API in Swagger 2.0. It is
# translated to OpenAPI 3 in memory; the drift is found as with the OpenAPI
# document (exit code 1).
set -u
cd "$(dirname "$0")/.."
. examples/_demo.sh

start_demo "$PORT"

show specsentinel examples/swagger2.yaml --url "http://127.0.0.1:$PORT"
exit "$last_code"
