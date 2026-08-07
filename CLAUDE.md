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
```

After editing a plugin's shipped files, reinstall/reload it in a running session to pick up changes. Every plugin script that needs its own root resolves it from `$0`'s location rather than assuming `CLAUDE_PLUGIN_ROOT` is set, since that variable is only exported to hooks, not to the shell running a slash command's `!` bash block — see the `script_dir=$(cd -- "$(dirname -- "$0")" ...)` pattern in `plugins/*/scripts/*.sh`. New plugin scripts should follow the same pattern.

## Plugins

### `comms` — communication styles

Shapes *how* Claude communicates (response format, tone, register), independent of task content. Controlled via `/comms:style [list|enable|disable] [feature]`.

Architecture:

- **Features** (`plugins/comms/features/<id>/feature.sh`) declare `FEATURE_NAME`, `FEATURE_DESC`, `FEATURE_EVENT`, optionally `FEATURE_GROUP`, and a `feature_run()` that prints the feature's text contribution to stdout. Sourced by both the dispatcher and the control CLI — must have no side effects at source time.
- **Dispatcher** (`hooks/dispatch.sh <Event>`), wired once per event in `hooks/hooks.json`, walks every installed feature, keeps the ones enabled for that event, concatenates their `feature_run()` output, and emits a single hook JSON envelope (`hookSpecificOutput.additionalContext`).
- **State** lives outside the plugin at `${CLAUDE_CONFIG_DIR:-~/.claude}/comms/`, so it survives plugin reinstalls/updates:
  - `plugin-disabled` file present → kill switch, whole plugin off.
  - Ungrouped feature (no `FEATURE_GROUP`) → default **on**; `disabled/<id>` marker turns it off.
  - Grouped feature (`FEATURE_GROUP` set) → default **off**; `enabled/<id>` marker turns it on. Members sharing a group are mutually exclusive — enabling one clears its siblings' markers (`comms-ctl.sh enable`), and `comms_group_winner()` in `lib/comms.sh` re-enforces at read time as a backstop.
- `lib/comms.sh` is the one shared helper, sourced by both `hooks/dispatch.sh` and `scripts/comms-ctl.sh` — the only place that should read/write feature state.

Current features are `bullets` and `checklist`, both in the `response-format` group (mutually exclusive, default off).

To add a feature: create `plugins/comms/features/<id>/feature.sh` following the contract above; if its `FEATURE_EVENT` isn't already wired, add one line to `hooks/hooks.json` pointing that event at `dispatch.sh <Event>`. No other wiring needed — it's auto-listed and auto-toggleable.

### `slog` — long-horizon work through a living document

Drives work too large for one chat exchange through a single markdown doc per feature (`docs/work/<slug>.md`) instead of chat back-and-forth. Command-only plugin — no hooks, no toggles.

- `/slog:start <slug>` — scaffold `docs/work/<slug>.md` from `plugins/slog/slog/template.md`, status `draft`.
- `/slog:resume` — find the doc that isn't `done`, report status + next actionable item, continue working it.
- `/slog:list` — list docs under `docs/work/` with their status.

`plugins/slog/scripts/slog.sh` does only the mechanical parts (scaffold, list); each command's markdown inlines the actual working protocol from `plugins/slog/slog/protocol.md` (doc structure, evidence model, lifecycle `draft → agreed → building → done`). Design rationale and the decisions behind the doc format are in `docs/discussion.md` — read it before changing the template or protocol.

## Add a plugin

1. `mkdir -p plugins/<name>/.claude-plugin`
2. Write `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, `description`).
3. Add its components (`hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`). Use `${CLAUDE_PLUGIN_ROOT}` for paths inside the plugin.
4. Register it in `.claude-plugin/marketplace.json` under `plugins`.
