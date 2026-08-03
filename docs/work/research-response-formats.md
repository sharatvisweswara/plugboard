# research-response-formats

**Status:** agreed
**Branch/PR:** —

## Goal

Survey response-format conventions from AI coding agents and general software/logging practice, then implement at least one new response-format as a selectable comms feature so users can pick a convention other than the current fixed bullet+prefix style.

## Definition of Done

| Criterion | Evidence type | Evidence |
|-----------|---------------|----------|
| Comparison of >=3 conventions from AI agent tools (Aider, Cursor, Cline, Copilot CLI, etc.) | pointer |  |
| Comparison of >=2 general software/logging conventions (syslog levels, conventional commits, RFC 2119, checklist styles) | pointer |  |
| Recommendation for which new format(s) to build, logged in Decisions | pointer |  |
| At least one new format feature implemented under `plugins/comms/features/` | pointer |  |
| Enabling the new format feature auto-disables the existing `response-format` feature (mutual exclusivity) | command |  |
| New feature toggles cleanly via `comms-ctl.sh` (list/enable/disable) | command |  |

## Decisions

- Survey both AI-agent tools and general software conventions, not just one. Why: AI-specific tools may share blind spots that general conventions don't.
- New response-format feature is a mutually exclusive alternative to the existing one, not stackable. Why: two active prefix/status conventions at once would produce conflicting or confusing output.

## Tasks

- [ ] Survey AI coding agent response-format conventions
- [ ] Survey general software/logging conventions
- [ ] Write comparison and recommend format(s) to build
- [ ] Implement new response-format feature(s) under `plugins/comms/features/`
- [ ] Add mutual-exclusivity handling to `comms-ctl.sh` (enabling one response-format feature disables others in the group)
- [ ] Verify via `comms list`/`enable`/`disable`

## Out of Scope

- Changing the existing `response-format` feature's default text
- A UI beyond the existing `comms-ctl.sh` CLI
