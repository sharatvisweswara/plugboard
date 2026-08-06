---
description: Resume the active slog doc — report status and next actionable item
allowed-tools: Bash(sh:*), Read, Edit, Write, Glob
---

Existing slog docs and their statuses:

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/slog.sh" list`

If exactly one doc is not `done`, that's the active one: open it, report its status and the single next actionable item, and continue working it. If several are active or none are, list them and ask which.

The protocol you are now running:

!`cat "${CLAUDE_PLUGIN_ROOT}/slog/protocol.md"`
