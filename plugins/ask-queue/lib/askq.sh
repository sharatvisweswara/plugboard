#!/bin/sh
# Shared helpers for the ask-queue hooks. Pure POSIX sh + curl.
# The daemon does all JSON parsing; hooks pass their stdin through untouched.

askq_port() {
  printf '%s\n' "${ASKQ_PORT:-7788}"
}

askq_url() {
  printf 'http://127.0.0.1:%s\n' "$(askq_port)"
}

askq_alive() {
  curl -sf --max-time 2 "$(askq_url)/health" > /dev/null 2>&1
}

# Start the daemon if it is not running. Returns non-zero when it still is
# not reachable after ~3s, so callers can fall back to the native picker.
askq_ensure_daemon() {
  askq_alive && return 0
  python3 "$1/server/askqd.py" --daemon > /dev/null 2>&1
  i=0
  while [ $i -lt 15 ]; do
    askq_alive && return 0
    sleep 0.2
    i=$((i + 1))
  done
  return 1
}
