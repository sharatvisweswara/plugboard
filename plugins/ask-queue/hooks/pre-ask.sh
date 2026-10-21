#!/bin/sh
# PreToolUse hook, matcher AskUserQuestion.
# askq_client.py queues the question with the hub (local daemon, or the URL in
# <state>/hub) and prints a deny whose reason tells the session to keep
# working. No output means the native picker shows as usual.

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
if ! command -v python3 >/dev/null 2>&1; then
  state="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/ask-queue"
  mkdir -p "$state" && printf '%s pre-ask[%s] no-python3 PATH="%s"\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$$" "$PATH" >>"$state/ask-queue.log"
  exit 0
fi
exec python3 "$root/server/askq_client.py" pre-ask
