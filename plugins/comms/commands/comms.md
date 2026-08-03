---
description: List and toggle comms communication-style features (list/enable/disable)
argument-hint: "[list|enable|disable] [feature]"
allowed-tools: Bash(sh:*)
---

Manage the `comms` plugin. Usage:

- `/comms` or `/comms list` — list features and their on/off state
- `/comms disable` — kill switch: turn the whole plugin off
- `/comms enable` — turn the whole plugin back on
- `/comms disable <feature>` — turn one feature off
- `/comms enable <feature>` — turn one feature on

Result of running the control script:

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/comms-ctl.sh" $ARGUMENTS`

Report the outcome to the user tersely. If they passed no arguments, present the feature list.
