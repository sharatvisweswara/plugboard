#!/bin/sh
# Stop hook, asyncRewake. Runs in the background after each turn.
# Long-polls the daemon for answers to this session's queued questions.
# 204 (nothing queued, or superseded by a newer waiter): exit 0, no wake.
# 200: print the answers to stderr and exit 2, which wakes the session.

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
. "$root/lib/askq.sh"

askq_alive || exit 0
tmp=$(mktemp "${TMPDIR:-/tmp}/askq.XXXXXX") || exit 0
trap 'rm -f "$tmp"' EXIT
code=$(curl -s -o "$tmp" -w '%{http_code}' -H 'Content-Type: application/json' \
  --data-binary @- "$(askq_url)/hook/wait")
[ "$code" = 200 ] || exit 0
cat "$tmp" >&2
exit 2
