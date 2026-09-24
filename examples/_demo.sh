# Shared helpers for the example scripts (sourced, not run on its own).
# Starts the demo API from examples/demo_server.py and stops it on exit.
PYTHON="${PYTHON:-python3}"
PORT="${PORT:-8099}"
_demo_pids=()

# start_demo PORT [--conform]
start_demo() {
  "$PYTHON" examples/demo_server.py --port "$@" >/dev/null 2>&1 &
  _demo_pids+=("$!")
  for _ in $(seq 1 100); do
    if "$PYTHON" -c "import socket, sys; socket.create_connection(('127.0.0.1', int(sys.argv[1])), 0.2)" "$1" 2>/dev/null; then
      return 0
    fi
    sleep 0.1
  done
  echo "The demo API did not start on port $1." >&2
  exit 2
}

stop_demo() {
  for pid in "${_demo_pids[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null
  done
  wait 2>/dev/null
}
trap stop_demo EXIT

# show COMMAND...: print the command like a terminal, run it, remember the exit code.
show() {
  echo "\$ $*"
  "$@"
  last_code=$?
  echo "(exit code $last_code)"
  echo
}
