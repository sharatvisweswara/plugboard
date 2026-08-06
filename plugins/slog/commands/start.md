---
description: Start a new slog — scaffold docs/work/<slug>.md and draft the goal
argument-hint: "<slug>"
allowed-tools: Bash(sh:*), Read, Edit, Write, Glob
---

Mechanical result of the scaffold:

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/slog.sh" start $ARGUMENTS`

If the script errored (bad slug, doc already exists), report that and stop.

Otherwise a new doc was just scaffolded at `docs/work/<slug>.md`. Open it, then work the **draft** phase: draft the Goal and Definition of Done with the user, and record any genuine open questions. Do not start implementing yet.

The protocol you are now running:

!`cat "${CLAUDE_PLUGIN_ROOT}/slog/protocol.md"`
