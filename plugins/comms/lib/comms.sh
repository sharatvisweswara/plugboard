#!/bin/sh
# Shared library for the comms plugin.
# Sourced by the hook dispatcher and the control CLI. Pure POSIX sh, no jq.
#
# State model (default = enabled):
#   <state>/plugin-disabled        present  -> whole plugin off (kill switch)
#   <state>/disabled/<feature-id>  present  -> that feature off
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
  mkdir -p "$(comms_state_dir)/disabled"
}

# True when the whole plugin is switched off.
comms_plugin_disabled() {
  [ -f "$(comms_state_dir)/plugin-disabled" ]
}

# True when a specific feature is switched off.
comms_feature_disabled() {
  [ -f "$(comms_state_dir)/disabled/$1" ]
}

# A feature is live only if the plugin is on AND the feature is not disabled.
comms_feature_enabled() {
  ! comms_plugin_disabled && ! comms_feature_disabled "$1"
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
