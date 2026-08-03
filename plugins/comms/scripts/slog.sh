#!/bin/sh
# slog scaffold/lookup helper. The /slog command carries the protocol;
# this script only does the mechanical bits: create a doc from the template,
# and list existing docs with their status. Operates on the current repo
# (docs are written under ./docs/work/), template comes from the plugin.

# Resolve the plugin root from this script's own location — CLAUDE_PLUGIN_ROOT
# is only exported to hooks, not to the shell that runs a slash command's !bash.
# slog.sh lives at <root>/scripts/slog.sh.
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P) || { echo "slog.sh: cannot resolve script dir" >&2; exit 1; }
COMMS_ROOT=$(dirname -- "$script_dir")
tpl="$COMMS_ROOT/slog/template.md"

cmd="${1:-list}"

case "$cmd" in
  start)
    slug="$2"
    [ -n "$slug" ] || { echo "usage: slog start <slug>" >&2; exit 1; }
    case "$slug" in
      *[!a-z0-9-]*) echo "slug must be lowercase letters, digits, and dashes: '$slug'" >&2; exit 1 ;;
    esac
    dest="docs/work/$slug.md"
    [ -e "$dest" ] && { echo "already exists, not overwriting: $dest" >&2; exit 1; }
    mkdir -p docs/work
    sed "s/<slug>/$slug/g" "$tpl" > "$dest"
    echo "created $dest (status: draft)"
    ;;
  list)
    if [ -d docs/work ]; then
      found=0
      for f in docs/work/*.md; do
        [ -e "$f" ] || continue
        found=1
        st="$(sed -n 's/^\*\*Status:\*\* *\([a-z]*\).*/\1/p' "$f" | head -1)"
        printf '%-44s %s\n' "$f" "${st:-?}"
      done
      [ "$found" = 1 ] || echo "no slog docs yet in docs/work/ — run: /slog start <slug>"
    else
      echo "no docs/work/ directory yet — run: /slog start <slug>"
    fi
    ;;
  *)
    echo "usage: slog [start <slug> | list]" >&2
    exit 1
    ;;
esac
