#!/usr/bin/env bash
# Usage: list-threads.sh [PR_NUMBER]
# Lists review threads with their GraphQL node IDs, resolved status, and root comment DB ID.

set -euo pipefail

OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO=$(gh repo view --json name --jq '.name')
PR=${1:-$(gh pr view --json number --jq '.number')}

gh api graphql -f query="
query {
  repository(owner: \"$OWNER\", name: \"$REPO\") {
    pullRequest(number: $PR) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          comments(first: 1) { nodes { databaseId } }
        }
      }
    }
  }
}" --jq '.data.repository.pullRequest.reviewThreads.nodes[] | {id, isResolved, commentId: .comments.nodes[0].databaseId}'
