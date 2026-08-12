#!/bin/sh
# comms control CLI. Switches the active style and lists available ones.
#
#   comms-ctl.sh [list|status]   show all styles and which is active
#   comms-ctl.sh <style>         switch to that style
#   comms-ctl.sh default         switch off — model's own judgment, no override

# Resolve the plugin root from this script's own location — CLAUDE_PLUGIN_ROOT
# is only exported to hooks, not to the shell that runs a slash command's !bash.
# comms-ctl.sh lives at <root>/scripts/comms-ctl.sh.
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P) || { echo "comms-ctl.sh: cannot resolve script dir" >&2; exit 1; }
COMMS_ROOT=$(dirname -- "$script_dir")
export COMMS_ROOT
. "$COMMS_ROOT/lib/comms.sh"
comms_ensure_state

print_list() {
  active="$(comms_active_style)"
  printf '%-18s %-8s %-16s %s\n' "STYLE" "ACTIVE" "EVENT" "DESCRIPTION"
  printf '%-18s %-8s %-16s %s\n' "-----" "------" "-----" "-----------"
  for id in $(comms_feature_ids); do
    st=""
    [ "$id" = "$active" ] && st="*"
    (
      . "$COMMS_ROOT/features/$id/feature.sh"
      printf '%-18s %-8s %-16s %s\n' "$id" "$st" "$FEATURE_EVENT" "$FEATURE_DESC"
    )
  done
  st=""
  [ "$active" = "default" ] && st="*"
  printf '%-18s %-8s %-16s %s\n' "default" "$st" "-" "no override — model's own judgment"
}

cmd="${1:-list}"

case "$cmd" in
  list|status)
    print_list
    ;;
  default)
    printf 'default\n' > "$(comms_style_file)"
    rm -rf "$(comms_state_dir)/enabled" "$(comms_state_dir)/disabled" "$(comms_state_dir)/plugin-disabled"
    echo "Style: default (no override — model's own judgment)."
    ;;
  *)
    if comms_feature_exists "$cmd"; then
      printf '%s\n' "$cmd" > "$(comms_style_file)"
      rm -rf "$(comms_state_dir)/enabled" "$(comms_state_dir)/disabled" "$(comms_state_dir)/plugin-disabled"
      echo "Style: $cmd."
    else
      echo "Unknown style: $cmd" >&2
      echo "Run '/comms:style' to see available styles." >&2
      exit 1
    fi
    ;;
esac
