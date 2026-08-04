# research-response-formats

**Status:** done
**Branch/PR:** —

## Goal

Survey response-format conventions from AI coding agents and general software/logging practice, then implement at least one new response-format as a selectable comms feature so users can pick a convention other than the current fixed bullet+prefix style.

## Definition of Done

- [x] Compare ≥3 AI-agent tool conventions (Aider, Cursor, Cline, Copilot CLI) — _evidence: pointer_ →
  [research-response-formats-survey.md](research-response-formats-survey.md) §"AI coding agents"
- [x] Compare ≥2 general software/logging conventions (syslog levels, conventional commits, RFC 2119, checklist styles) — _evidence: pointer_ →
  [research-response-formats-survey.md](research-response-formats-survey.md) §"General software / logging conventions"
- [x] Recommend which new format(s) to build, logged in Decisions — _evidence: pointer_ →
  [research-response-formats-survey.md](research-response-formats-survey.md) §"Recommendation"; Decisions section below
- [x] Implement ≥1 new format feature under `plugins/comms/features/` — _evidence: pointer_ →
  `plugins/comms/features/response-format-checklist/feature.sh`
- [x] Enabling the new format auto-disables the existing `response-format` (mutual exclusivity), both directions — _evidence: command_
    ```
    $ comms-ctl.sh enable response-format-checklist   # with response-format on
    Feature 'response-format' disabled (mutually exclusive with 'response-format-checklist').
    Feature 'response-format-checklist' enabled.
    ```
- [x] Grouped features default OFF at install (opt-in only), never both-on by default — _evidence: command_
    ```
    $ comms-ctl.sh list   # fresh CLAUDE_CONFIG_DIR, no state files
    response-format-checklist disabled
    response-format           disabled
    ```
- [x] New feature toggles cleanly via `comms-ctl.sh` (list/enable/disable) — _evidence: command_
    <!-- run against an isolated CLAUDE_CONFIG_DIR; both features list, toggle, and re-enable correctly -->
    ```
    $ comms-ctl.sh disable response-format-checklist && comms-ctl.sh list
    Feature 'response-format-checklist' disabled.
    response-format-checklist disabled
    response-format           disabled
    ```

## Decisions

- Survey both AI-agent tools and general software conventions, not just one. Why: AI-specific tools may share blind spots that general conventions don't.
- New response-format feature is a mutually exclusive alternative to the existing one, not stackable. Why: two active prefix/status conventions at once would produce conflicting or confusing output.
- Mutual exclusivity implemented as a generic `FEATURE_GROUP` tag (feature.sh metadata) rather than a one-off `response-format`-specific check in comms-ctl.sh. Why: any future feature pair needing the same "enabling one disables its siblings" behavior can opt in by setting the same group, no CLI changes needed.
- Grouped features default OFF (opt-in via explicit `enable`) rather than the plugin's normal default-ON/opt-out. Why: default-on would have raced group members against each other at install time (both start enabled, neither disabled the other) — surfaced live when both `response-format` and `response-format-checklist` were on simultaneously right after this feature landed. Opt-in-only means installing a new grouped feature never silently activates it.
- Built the checklist convention (Cline-style pending/in_progress/completed/blocked, one in_progress at a time) as the new format, not a syslog/conventional-commits reskin. Why: syslog and conventional commits are structurally the same shape as the existing tag-per-line format; the checklist is the one surveyed convention that's actually different (state persists across turns instead of being restated).

## Tasks

- [x] Survey AI coding agent response-format conventions
- [x] Survey general software/logging conventions
- [x] Write comparison and recommend format(s) to build
- [x] Implement new response-format feature(s) under `plugins/comms/features/`
- [x] Add mutual-exclusivity handling to `comms-ctl.sh` (enabling one response-format feature disables others in the group)
- [x] Verify via `comms list`/`enable`/`disable`

## Out of Scope

- Changing the existing `response-format` feature's default text
- A UI beyond the existing `comms-ctl.sh` CLI
