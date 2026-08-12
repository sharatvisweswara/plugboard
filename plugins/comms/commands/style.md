---
description: List or switch the comms plugin's active communication style
argument-hint: "[<style>|default|list]"
allowed-tools: Bash(sh:*)
---

Manage the `comms` plugin's communication style. At most one is active at a time. Usage:

- `/comms:style` or `/comms:style list` — list styles and which one is active
- `/comms:style <style>` — switch to that style
- `/comms:style default` — switch off — no override, model's own judgment

Result of running the control script:

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/comms-ctl.sh" $ARGUMENTS`

Print the script's output verbatim in a code block, unedited — no summarizing, paraphrasing, or commentary. The output above already is the report.
