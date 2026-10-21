#!/bin/sh
# Stop hook, asyncRewake. Runs in the background after each turn.
# askq_client.py sends any spooled questions, then long-polls the hub for
# answers to this session's questions. Exit 2 with the answers on stderr
# wakes the session; exit 0 means there was nothing to wait for.

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
if ! command -v python3 >/dev/null 2>&1; then
  state="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/ask-queue"
  mkdir -p "$state" && printf '%s wait[%s] no-python3 PATH="%s"\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$$" "$PATH" >>"$state/ask-queue.log"
  exit 0
fi
exec python3 "$root/server/askq_client.py" wait
