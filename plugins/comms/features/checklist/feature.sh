#!/bin/sh
# Feature: checklist
# Sourced by the dispatcher and the control CLI. Must only declare metadata
# and define feature_run(); no side effects at source time.

FEATURE_NAME="Checklist"
FEATURE_DESC="Persistent checklist with pending/in_progress/completed/blocked status and agent/user owner."
FEATURE_EVENT="UserPromptSubmit"

# Prints this feature's contribution to the event's additionalContext.
feature_run() {
  cat <<'EOF'
Response format: track work as a checklist, not prose narration. Each item has a status (pending, in_progress, completed, or blocked) and an owner (agent or user). Agent items are work the agent does; user items are actions, decisions, or answers only the user can provide. Only one agent item may be in_progress at a time. Show the checklist when it changes; when nothing changed, don't repeat it. Mark an item completed the moment it's done rather than narrating the completion in text, and add new items as pending as soon as they're discovered. Open with the checklist, skip preamble.

Rules: prefix every item with its status emoji — ⬜ pending, 🔄 in_progress, ✅ completed, 🚫 blocked — never the literal words "pending"/"in_progress"/etc. and never plain brackets like "[completed]". Use exactly these four emojis for these four statuses, no substitutes. After the status emoji, tag every item with its owner emoji — 🤖 agent, 👤 user — e.g. "⬜ 👤 pick a deploy target". When an item is blocked on the user, mark it 🚫 and add a separate 👤 item for what the user must do.
EOF
}
