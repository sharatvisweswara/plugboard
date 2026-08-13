#!/bin/sh
# SessionStart hook for the simple-english plugin.
#
# Registered on matcher startup|resume|clear|fork|compact — fires once at
# every session boundary and again after every context compaction, so the
# ruleset survives long sessions without needing per-turn reinjection
# (unlike a UserPromptSubmit hook). See docs/work/simple-english.md for why.
#
# Single source of truth: cats the same SKILL.md that's also independently
# reachable as a model-invoked Skill.

: "${CLAUDE_PLUGIN_ROOT:?session-start.sh: CLAUDE_PLUGIN_ROOT unset}"

# Minimal JSON string escaping (backslash, quote, tab; newlines -> \n).
# Content is plain prose/markdown, so this is sufficient.
json_escape() {
  awk 'BEGIN{ORS=""} {
    gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); gsub(/\t/,"\\t")
    if (NR>1) printf "\\n"
    printf "%s", $0
  }'
}

content="$(cat "$CLAUDE_PLUGIN_ROOT/skills/simple-english/SKILL.md")"
esc="$(printf '%s' "$content" | json_escape)"
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$esc"
