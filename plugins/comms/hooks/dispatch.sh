#!/bin/sh
# Generic hook dispatcher for the comms plugin.
#
# Registered once per event in hooks.json as: dispatch.sh <EventName>
# It collects the text contribution of every enabled feature whose
# FEATURE_EVENT matches <EventName>, joins them, and emits the single JSON
# envelope that event expects. Read-only w.r.t. state.
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

# Kill switch: whole plugin off -> contribute nothing.
comms_plugin_disabled && exit 0

# Minimal JSON string escaping (backslash, quote, tab; newlines -> \n).
# Content is plain prose, so this is sufficient.
json_escape() {
  awk 'BEGIN{ORS=""} {
    gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); gsub(/\t/,"\\t")
    if (NR>1) printf "\\n"
    printf "%s", $0
  }'
}

contributions=""
for id in $(comms_feature_ids); do
  comms_feature_enabled "$id" || continue
  out="$(
    . "$CLAUDE_PLUGIN_ROOT/features/$id/feature.sh"
    [ "$FEATURE_EVENT" = "$event" ] || exit 0
    feature_run
  )" || continue
  [ -n "$out" ] || continue
  if [ -n "$contributions" ]; then
    contributions="$contributions

$out"
  else
    contributions="$out"
  fi
done

[ -n "$contributions" ] || exit 0

esc="$(printf '%s' "$contributions" | json_escape)"
printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$event" "$esc"
