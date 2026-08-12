#!/usr/bin/env bash
# Usage: reply-to-thread.sh COMMENT_ID "Reply text" [PR_NUMBER]
# Posts a reply to an inline review thread.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: reply-to-thread.sh COMMENT_ID \"Reply text\" [PR_NUMBER]" >&2
  exit 1
fi

COMMENT_ID=$1
BODY=$2
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
PR=${3:-$(gh pr view --json number --jq '.number')}

gh api "repos/$REPO/pulls/$PR/comments" \
  --method POST \
  -F "in_reply_to=$COMMENT_ID" \
  -f "body=$BODY" \
  --jq '{id, created_at}'
