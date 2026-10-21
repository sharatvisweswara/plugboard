#!/bin/sh
# PreToolUse hook, matcher AskUserQuestion.
# Queues the question in the daemon and denies the tool call with a reason
# that tells the session to keep working. Any failure exits 0 with no output,
# so the native picker shows as usual.

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
. "$root/lib/askq.sh"

askq_ensure_daemon "$root" || exit 0
out=$(curl -sf --max-time 10 -H 'Content-Type: application/json' \
  --data-binary @- "$(askq_url)/hook/pre-ask") || exit 0
printf '%s\n' "$out"
