#!/bin/sh
# Shared library for the comms plugin.
# Sourced by the hook dispatcher and the control CLI. Pure POSIX sh, no jq.
#
# State model:
#   <state>/plugin-disabled        present  -> whole plugin off (kill switch)
#   ungrouped feature (no FEATURE_GROUP):    default ON, opt-out
#     <state>/disabled/<feature-id>  present -> that feature off
#   grouped feature (FEATURE_GROUP set):     default OFF, opt-in
#     <state>/enabled/<feature-id>   present -> that feature on
#     (features sharing a group are mutually exclusive: see comms-ctl.sh enable)
# State lives outside the plugin so it survives reinstalls/updates.

# Directory holding persistent enable/disable state.
comms_state_dir() {
  printf '%s/comms\n' "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
}

# Plugin install root. Dispatcher/CLI export COMMS_ROOT; fall back to the
# plugin var Claude Code sets for hooks.
comms_root() {
  printf '%s\n' "${COMMS_ROOT:-$CLAUDE_PLUGIN_ROOT}"
}

# Create the state dirs. Only the CLI (which mutates state) needs this;
# the dispatcher is read-only and works without it.
comms_ensure_state() {
  mkdir -p "$(comms_state_dir)/disabled" "$(comms_state_dir)/enabled"
}

# True when the whole plugin is switched off.
comms_plugin_disabled() {
  [ -f "$(comms_state_dir)/plugin-disabled" ]
}

# True when a specific (ungrouped, default-on) feature is switched off.
comms_feature_disabled() {
  [ -f "$(comms_state_dir)/disabled/$1" ]
}

# True when a specific (grouped, default-off) feature has been explicitly enabled.
comms_feature_opted_in() {
  [ -f "$(comms_state_dir)/enabled/$1" ]
}

# Would this feature run, ignoring the plugin-wide kill switch?
# Grouped features are opt-in (off until explicitly enabled); ungrouped
# features are opt-out (on until explicitly disabled). For a grouped feature
# the read-time invariant "at most one member of a group runs" is enforced
# here — even if several enabled/ markers somehow coexist, only the group
# winner runs, so a stray marker can't revive the both-on bug.
comms_feature_would_run() {
  group="$(comms_feature_group "$1")"
  if [ -n "$group" ]; then
    comms_feature_opted_in "$1" || return 1
    [ "$(comms_group_winner "$group")" = "$1" ]
  else
    ! comms_feature_disabled "$1"
  fi
}

# A feature is live only if the plugin is on AND it would run per its own state.
comms_feature_enabled() {
  ! comms_plugin_disabled && comms_feature_would_run "$1"
}

# True when <id> names a real, installed feature.
comms_feature_exists() {
  [ -f "$(comms_root)/features/$1/feature.sh" ]
}

# Print every installed feature id, one per line.
comms_feature_ids() {
  root="$(comms_root)"
  for d in "$root"/features/*/; do
    [ -f "${d}feature.sh" ] || continue
    id="${d%/}"
    printf '%s\n' "${id##*/}"
  done
}

# Print a feature's FEATURE_GROUP (empty if it belongs to no group).
# Features sharing a non-empty group are mutually exclusive: enabling one
# disables the others (see comms-ctl.sh enable).
comms_feature_group() {
  (
    . "$(comms_root)/features/$1/feature.sh"
    printf '%s\n' "${FEATURE_GROUP:-}"
  )
}

# The single opted-in feature that wins a group: the first opted-in member in
# feature-id order (glob expansion is lexicographically sorted, so this is
# deterministic). Prints nothing if no member is opted in. Enabling via
# comms-ctl.sh already clears siblings, so normally exactly one is opted in;
# this is the read-time backstop when that invariant is somehow violated.
comms_group_winner() {
  group="$1"
  for id in $(comms_feature_ids); do
    [ "$(comms_feature_group "$id")" = "$group" ] || continue
    comms_feature_opted_in "$id" || continue
    printf '%s\n' "$id"
    return 0
  done
}
