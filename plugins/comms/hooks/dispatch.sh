#!/bin/sh
# Generic hook dispatcher for the comms plugin.
#
# Registered once per event in hooks.json as: dispatch.sh <EventName>
# Prints the active style's contribution, if its FEATURE_EVENT matches
# <EventName>, as the single JSON envelope that event expects. Read-only
# w.r.t. state.
#
# Feature contract (features/<id>/feature.sh):
#   FEATURE_NAME  human label
#   FEATURE_DESC  one-line description
#   FEATURE_EVENT hook event name (e.g. UserPromptSubmit)
#   feature_run() prints the plain-text contribution to stdout

event="$1"
: "${CLAUDE_PLUGIN_ROOT:?dispatch.sh: CLAUDE_PLUGIN_ROOT unset}"
COMMS_ROOT="$CLAUDE_PLUGIN_ROOT"
export COMMS_ROOT
. "$CLAUDE_PLUGIN_ROOT/lib/comms.sh"

active="$(comms_active_style)"
[ "$active" = "default" ] && exit 0
comms_feature_exists "$active" || exit 0

# Minimal JSON string escaping (backslash, quote, tab; newlines -> \n).
# Content is plain prose, so this is sufficient.
json_escape() {
  awk 'BEGIN{ORS=""} {
    gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); gsub(/\t/,"\\t")
    if (NR>1) printf "\\n"
    printf "%s", $0
  }'
}

out="$(
  . "$CLAUDE_PLUGIN_ROOT/features/$active/feature.sh"
  [ "$FEATURE_EVENT" = "$event" ] || exit 0
  feature_run
)"
[ -n "$out" ] || exit 0

esc="$(printf '%s' "$out" | json_escape)"
printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$event" "$esc"
