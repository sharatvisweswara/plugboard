#!/bin/sh
# Start the daemon if needed, open the inbox page, and print every URL it
# serves (the tailnet one works from a phone on the same tailnet).

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
. "$root/lib/askq.sh"

if askq_ensure_daemon "$root"; then
  open "$(askq_url)"
  curl -sf --max-time 2 "$(askq_url)/health" |
    python3 -c 'import json, sys; print("inbox: " + "  ".join(json.load(sys.stdin)["urls"]))'
else
  echo "ask-queue daemon failed to start; see ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/ask-queue/askqd.log"
fi
