#!/bin/sh
# Feature: response-format
# Sourced by the dispatcher and the control CLI. Must only declare metadata
# and define feature_run(); no side effects at source time.

FEATURE_NAME="Response format hint"
FEATURE_DESC="Terse bullets prefixed with [DONE]/[TODO]/[INFO]/[WARN]."
FEATURE_EVENT="UserPromptSubmit"

# Prints this feature's contribution to the event's additionalContext.
feature_run() {
  cat <<'EOF'
Response format: reply in brief bullet points or short paragraphs. Prefix each with one of [DONE], [TODO LOW|MEDIUM|HIGH], [INFO], or [WARN] as appropriate. Defer long explanations until explicitly asked for more detail.
EOF
}
