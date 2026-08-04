---
description: List and toggle comms communication-style features (list/enable/disable)
argument-hint: "[list|enable|disable] [feature]"
allowed-tools: Bash(sh:*)
---

Manage the `comms` plugin's communication-style features. Usage:

- `/comms:style` or `/comms:style list` — list features and their on/off state
- `/comms:style disable` — kill switch: turn the whole plugin off
- `/comms:style enable` — turn the whole plugin back on
- `/comms:style disable <feature>` — turn one feature off
- `/comms:style enable <feature>` — turn one feature on

Result of running the control script:

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/comms-ctl.sh" $ARGUMENTS`

Report the outcome to the user tersely. If they passed no arguments, present the feature list.
