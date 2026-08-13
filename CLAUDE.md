# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins) — a place to build, install, and experiment with plugins. There is no build/lint/test tooling; plugins are POSIX `sh` scripts plus markdown command/skill files, developed by editing and reinstalling.

```
.claude-plugin/marketplace.json   # marketplace manifest, lists all plugins
plugins/<name>/
  .claude-plugin/plugin.json       # plugin manifest (name, version, description)
  hooks/  commands/  agents/  skills/   # whatever the plugin ships
```

## Working with plugins locally

```
/plugin marketplace add .
/plugin install comms@plugboard
/plugin install slog@plugboard
/plugin install autoland@plugboard
/plugin install cleanup@plugboard
```

After editing a plugin's shipped files, reinstall/reload it in a running session to pick up changes. Every plugin script that needs its own root resolves it from `$0`'s location rather than assuming `CLAUDE_PLUGIN_ROOT` is set, since that variable is only exported to hooks, not to the shell running a slash command's `!` bash block — see the `script_dir=$(cd -- "$(dirname -- "$0")" ...)` pattern in `plugins/*/scripts/*.sh`. New plugin scripts should follow the same pattern.

## Plugins

### `comms` — communication styles

Shapes *how* Claude communicates (response format, tone, register), independent of task content. At most one style is active at a time. Controlled via `/comms:style [<style>|default|list]`.

Architecture:

- **Features** (`plugins/comms/features/<id>/feature.sh`), each one a style, declare `FEATURE_NAME`, `FEATURE_DESC`, `FEATURE_EVENT`, and a `feature_run()` that prints the feature's text contribution to stdout. Sourced by both the dispatcher and the control CLI — must have no side effects at source time.
- **Dispatcher** (`hooks/dispatch.sh <Event>`), wired once per event in `hooks/hooks.json`, reads the active style, runs its `feature_run()` if its `FEATURE_EVENT` matches the firing event, and emits a single hook JSON envelope (`hookSpecificOutput.additionalContext`).
- **State** lives outside the plugin at `${CLAUDE_CONFIG_DIR:-~/.claude}/comms/style`, so it survives plugin reinstalls/updates — one file holding the active feature id, or `default` for no override. `comms-ctl.sh <name>` overwrites it; switching is exclusive by construction, no group bookkeeping needed.
- `lib/comms.sh` is the one shared helper, sourced by both `hooks/dispatch.sh` and `scripts/comms-ctl.sh` — the only place that should read/write this state.

Current styles are `bullets` and `checklist`.

To add a style: create `plugins/comms/features/<id>/feature.sh` following the contract above; if its `FEATURE_EVENT` isn't already wired, add one line to `hooks/hooks.json` pointing that event at `dispatch.sh <Event>`. No other wiring needed — it's auto-listed and auto-selectable.

### `slog` — long-horizon work through a living document

Drives work too large for one chat exchange through a single markdown doc per feature (`docs/work/<slug>.md`) instead of chat back-and-forth. Command-only plugin — no hooks, no toggles.

- `/slog:start <slug>` — scaffold `docs/work/<slug>.md` from `plugins/slog/slog/template.md`, status `draft`.
- `/slog:resume` — find the doc that isn't `done`, report status + next actionable item, continue working it.
- `/slog:list` — list docs under `docs/work/` with their status.

`plugins/slog/scripts/slog.sh` does only the mechanical parts (scaffold, list); each command's markdown inlines the actual working protocol from `plugins/slog/slog/protocol.md` (doc structure, evidence model, lifecycle `draft → agreed → building → done`). Design rationale and the decisions behind the doc format are in `docs/discussion.md` — read it before changing the template or protocol.

### `autoland` — unattended commit-to-merge

`plugins/autoland/skills/autoland/SKILL.md`, `disable-model-invocation: true` — only fires on explicit invocation ("land this PR", or the `/autoland:autoland` command), never auto-triggered by the model. `commands/autoland.md` is a thin wrapper that `cat`s the skill file in and tells the model to start phase 1 immediately — same pattern slog's commands use for `slog/protocol.md`. Plugin commands are always namespaced by plugin name, so this can't be shortened to a bare `/autoland`. Five phases (commit/push/PR → request Copilot review → resolve comments → watch CI and fix breaks → merge), looping back into phases 3/4 whenever a push produces new review comments or new CI results. No hooks, no state.

Self-contained: phase 3 uses its own bundled scripts at `plugins/autoland/skills/autoland/scripts/*.sh` (fetch comments, list review threads, reply, resolve via GraphQL) — no dependency on any personal `~/.claude/skills/` content.

### `cleanup` — dry-run-then-confirm worktree tidying

Single skill (`plugins/cleanup/skills/cleanup/SKILL.md`). Scoped to the current worktree only — never enumerates or touches other worktrees. Phase 1 inventories (read-only): merged remote branch, per-worktree Docker containers, stale dev processes, implemented `plans/*.md`, scratch/secrets files. Phase 2 reports and calls `AskUserQuestion` (multi-select) — nothing is proposed without an explicit action a user can pick. Phase 3 applies only the confirmed categories. Never deletes the worktree itself or its checked-out local branch — that's left to whatever coordinates worktrees at the box level.

## Add a plugin

1. `mkdir -p plugins/<name>/.claude-plugin`
2. Write `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, `description`).
3. Add its components (`hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`). Use `${CLAUDE_PLUGIN_ROOT}` for paths inside the plugin.
4. Register it in `.claude-plugin/marketplace.json` under `plugins`.
