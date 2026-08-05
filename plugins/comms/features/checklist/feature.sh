#!/bin/sh
# Feature: checklist
# Sourced by the dispatcher and the control CLI. Must only declare metadata
# and define feature_run(); no side effects at source time.

FEATURE_NAME="Checklist"
FEATURE_DESC="Persistent checklist with pending/in_progress/completed/blocked status."
FEATURE_EVENT="UserPromptSubmit"
FEATURE_GROUP="response-format"

# Prints this feature's contribution to the event's additionalContext.
feature_run() {
  cat <<'EOF'
Response format: track work as a checklist, not prose narration. Each item has a status: pending, in_progress, completed, or blocked. Only one item may be in_progress at a time. Show the checklist when it changes; when nothing changed, don't repeat it. Mark an item completed the moment it's done rather than narrating the completion in text, and add new items as pending as soon as they're discovered. Open with the checklist, skip preamble.
EOF
}
