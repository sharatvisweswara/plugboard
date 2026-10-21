#!/bin/sh
# Start the daemon if needed and open the inbox page.

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
. "$root/lib/askq.sh"

if askq_ensure_daemon "$root"; then
  open "$(askq_url)"
  echo "opened $(askq_url)"
else
  echo "ask-queue daemon failed to start; see ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/ask-queue/askqd.log"
fi
