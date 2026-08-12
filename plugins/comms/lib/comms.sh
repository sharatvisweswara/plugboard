#!/bin/sh
# Shared library for the comms plugin.
# Sourced by the hook dispatcher and the control CLI. Pure POSIX sh, no jq.
#
# State model: at most one style is active at a time.
#   <state>/style   contains the active feature id, or "default"/absent for none.
# State lives outside the plugin so it survives reinstalls/updates.

# Directory holding persistent state.
comms_state_dir() {
  printf '%s/comms\n' "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
}

# Plugin install root. Dispatcher/CLI export COMMS_ROOT; fall back to the
# plugin var Claude Code sets for hooks.
comms_root() {
  printf '%s\n' "${COMMS_ROOT:-$CLAUDE_PLUGIN_ROOT}"
}

# Create the state dir. Only the CLI (which mutates state) needs this;
# the dispatcher is read-only and works without it.
comms_ensure_state() {
  mkdir -p "$(comms_state_dir)"
}

comms_style_file() {
  printf '%s/style\n' "$(comms_state_dir)"
}

# Print the active style id, or "default" if none is set.
# Falls back to a pre-3.0 enabled/<id> marker (old grouped-toggle state) so
# an existing choice survives the upgrade; the next `style <name>` call
# writes the new-format file and clears the legacy markers.
comms_active_style() {
  f="$(comms_style_file)"
  if [ -f "$f" ]; then
    s="$(cat "$f")"
    if [ -n "$s" ] && { [ "$s" = "default" ] || comms_feature_exists "$s"; }; then
      printf '%s\n' "$s"
      return
    fi
  fi
  d="$(comms_state_dir)/enabled"
  if [ -d "$d" ]; then
    for id in $(comms_feature_ids); do
      [ -f "$d/$id" ] || continue
      printf '%s\n' "$id"
      return
    done
  fi
  printf 'default\n'
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

# True when <id> is the currently active style.
comms_feature_enabled() {
  [ "$(comms_active_style)" = "$1" ]
}
