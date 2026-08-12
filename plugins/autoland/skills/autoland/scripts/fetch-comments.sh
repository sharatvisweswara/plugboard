#!/usr/bin/env bash
# Usage: fetch-comments.sh [PR_NUMBER]
# Outputs inline review comments and general PR comments as JSON arrays.
# Auto-detects owner/repo/PR from git context if PR_NUMBER is not provided.

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
PR=${1:-$(gh pr view --json number --jq '.number')}

echo "=== Inline review comments (REPO=$REPO PR=$PR) ===" >&2
gh api "repos/$REPO/pulls/$PR/comments" \
  --jq '[.[] | {id, user: .user.login, path, line, body, in_reply_to_id}]'

echo "" >&2
echo "=== General PR comments ===" >&2
gh api "repos/$REPO/issues/$PR/comments" \
  --jq '[.[] | {id, user: .user.login, body}]'
