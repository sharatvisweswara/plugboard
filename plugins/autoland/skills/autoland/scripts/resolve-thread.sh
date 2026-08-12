#!/usr/bin/env bash
# Usage: resolve-thread.sh THREAD_NODE_ID
# Resolves a review thread via GraphQL mutation.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: resolve-thread.sh THREAD_NODE_ID" >&2
  exit 1
fi

THREAD_ID=$1

gh api graphql -f query="
mutation {
  resolveReviewThread(input: {threadId: \"$THREAD_ID\"}) {
    thread { id isResolved }
  }
}" --jq '.data.resolveReviewThread.thread'
