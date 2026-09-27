#!/bin/sh
# Feature: bullets
# Sourced by the dispatcher and the control CLI. Must only declare metadata
# and define feature_run(); no side effects at source time.

FEATURE_NAME="Bullets"
FEATURE_DESC="Sectioned reply: Done / Info / Warning / Todo, with priority-tagged todos split into agent and user."
FEATURE_EVENT="UserPromptSubmit"

# Prints this feature's contribution to the event's additionalContext.
feature_run() {
  cat <<'EOF'
Response format: group your reply into labeled sections in this exact order, and omit any section that has no items:

✅ Done:
* completed results

ℹ️ Info:
* observations, context, neutral facts

⚠️ Warning:
* risks, cautions, things that could break

📋 Todo:
🤖 Agent (I will do these):
* 🔴 high-priority item
* 🟡 medium-priority item
👤 User (you must do or decide these):
* 🟢 low-priority item

Rules: use exactly these section emojis, labels, and order (Done, Info, Warning, Todo). Show a section header only when it has at least one item — never an empty section. Place each point under the section matching its nature; do not tag individual lines with [DONE]/[INFO]/etc. In Todo, split items into two subgroups: 🤖 Agent (work the agent will do next) and 👤 User (actions, decisions, or answers only the user can provide). Show a subgroup only when it has items, and list 🤖 Agent first. Prefix every Todo item with its priority emoji (🔴 high, 🟡 medium, 🟢 low); priorities apply within each subgroup and either subgroup can hold any priority. Keep each item to one line; defer long explanations until explicitly asked for more detail.
EOF
}
