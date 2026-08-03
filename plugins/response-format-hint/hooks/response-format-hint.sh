#!/bin/sh
# UserPromptSubmit hook: injects a response-format instruction into context.
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Response format: reply in brief bullet points or short paragraphs. Prefix each with one of [DONE], [TODO LOW|MEDIUM|HIGH], [INFO], or [WARN] as appropriate. Defer long explanations until explicitly asked for more detail."}}
EOF
