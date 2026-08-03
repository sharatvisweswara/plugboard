#!/bin/sh
# comms control CLI. Drives enable/disable state and lists features.
#
#   comms-ctl.sh list | status          show plugin + per-feature state
#   comms-ctl.sh enable                 turn the whole plugin on
#   comms-ctl.sh disable                turn the whole plugin off (kill switch)
#   comms-ctl.sh enable  <feature>      turn one feature on
#   comms-ctl.sh disable <feature>      turn one feature off

: "${CLAUDE_PLUGIN_ROOT:?comms-ctl.sh: CLAUDE_PLUGIN_ROOT unset}"
COMMS_ROOT="$CLAUDE_PLUGIN_ROOT"
export COMMS_ROOT
. "$CLAUDE_PLUGIN_ROOT/lib/comms.sh"
comms_ensure_state

cmd="${1:-list}"
arg="$2"

print_list() {
  if comms_plugin_disabled; then
    echo "Plugin 'comms': DISABLED (kill switch on — all features suppressed)"
  else
    echo "Plugin 'comms': enabled"
  fi
  echo
  printf '%-18s %-9s %-16s %s\n' "FEATURE" "STATUS" "EVENT" "DESCRIPTION"
  printf '%-18s %-9s %-16s %s\n' "-------" "------" "-----" "-----------"
  for id in $(comms_feature_ids); do
    if comms_feature_disabled "$id"; then st="disabled"; else st="enabled"; fi
    (
      . "$COMMS_ROOT/features/$id/feature.sh"
      printf '%-18s %-9s %-16s %s\n' "$id" "$st" "$FEATURE_EVENT" "$FEATURE_DESC"
    )
  done
}

case "$cmd" in
  list|status|"")
    print_list
    ;;
  enable)
    if [ -z "$arg" ]; then
      rm -f "$(comms_state_dir)/plugin-disabled"
      echo "Plugin 'comms' enabled."
    elif comms_feature_exists "$arg"; then
      rm -f "$(comms_state_dir)/disabled/$arg"
      echo "Feature '$arg' enabled."
    else
      echo "Unknown feature: $arg" >&2
      echo "Run 'comms list' to see available features." >&2
      exit 1
    fi
    ;;
  disable)
    if [ -z "$arg" ]; then
      touch "$(comms_state_dir)/plugin-disabled"
      echo "Plugin 'comms' disabled — all features suppressed until re-enabled."
    elif comms_feature_exists "$arg"; then
      touch "$(comms_state_dir)/disabled/$arg"
      echo "Feature '$arg' disabled."
    else
      echo "Unknown feature: $arg" >&2
      echo "Run 'comms list' to see available features." >&2
      exit 1
    fi
    ;;
  *)
    echo "usage: comms [list|status] | enable [<feature>] | disable [<feature>]" >&2
    exit 1
    ;;
esac
