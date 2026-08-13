# plugboard

Personal [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins). A place to build, install, and experiment with plugins.

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest, lists all plugins
plugins/<name>/
  .claude-plugin/plugin.json       # plugin manifest
  hooks/        commands/  agents/  skills/   # whatever the plugin ships
```

## Use it

Add this marketplace, then install a plugin:

```
/plugin marketplace add .
/plugin install comms@plugboard
/plugin install slog@plugboard
/plugin install autoland@plugboard
/plugin install cleanup@plugboard
```

## Plugins

### `comms` — communication styles

Features that shape *how Claude communicates* (response format, tone, register). At most one style is active at a time — picking one switches off whatever was active before. Control it with the `/comms:style` command:

| Command | Effect |
| --- | --- |
| `/comms:style` or `/comms:style list` | list styles + which one is active |
| `/comms:style <style>` | switch to that style |
| `/comms:style default` | switch off — no override, model's own judgment |
| `/comms:summary` | one-off: dump current task status as an executive summary (verdict line + detail) |

`/comms:summary` is a plain command, not a style — it runs once when invoked rather than shaping every reply.

Current styles:

| Style | Event | What it does |
| --- | --- | --- |
| `bullets` | UserPromptSubmit | Reply grouped into sections — ✅ Done, ℹ️ Info, ⚠️ Warning, 📋 Todo — with priority-tagged (🔴/🟡/🟢) todos. |
| `checklist` | UserPromptSubmit | Persistent checklist, one `in_progress` at a time — items prefixed ⬜/🔄/✅/🚫 for pending/in_progress/completed/blocked. |

`default` is always available too — no style file fires, Claude uses its own judgment.

#### How the toggle infrastructure works

A single dispatcher (`hooks/dispatch.sh <Event>`) runs per hook event. It reads the one active style, runs its `feature_run()` if its `FEATURE_EVENT` matches, and emits a single hook JSON envelope. State lives outside the plugin at `${CLAUDE_CONFIG_DIR:-~/.claude}/comms/style` (one file holding the active style id, or `default`) so it survives reinstalls.

`scripts/comms-ctl.sh` is the one place that writes this state; `lib/comms.sh` is the shared helper both it and the dispatcher source.

#### Add a style to `comms`

1. `mkdir plugins/comms/features/<id>`
2. Write `features/<id>/feature.sh` declaring `FEATURE_NAME`, `FEATURE_DESC`, `FEATURE_EVENT`, and a `feature_run()` that prints the contribution. No side effects at source time.
3. If its `FEATURE_EVENT` is one the dispatcher isn't wired for yet, add one line to `hooks/hooks.json` pointing that event at `dispatch.sh <Event>`.

It's then auto-listed and auto-selectable — no other wiring.

### `slog` — long-horizon work through a living document

For work too big for one exchange, `/slog` drives everything through a single markdown doc per feature (`docs/work/<slug>.md`) instead of chat back-and-forth. The doc holds the goal, a Definition of Done whose criteria each declare their evidence type, open questions, diagrams-first design, an append-only decisions log, and a task checklist. The agent works the doc, records evidence inline, and auto-advances status (`draft → agreed → building → done`) as each gate is met — surfacing to chat only for blocking questions, sign-off, or the done-gate.

| Command | Effect |
| --- | --- |
| `/slog:start <slug>` | scaffold `docs/work/<slug>.md` from the template, status `draft` |
| `/slog:resume` | resume the active doc — report status + next actionable item |
| `/slog:list` | list docs under `docs/work/` with their status |

slog is a command-only plugin — no hooks, no toggles. Each command inlines the shared protocol from `slog/protocol.md`; `scripts/slog.sh` only does the mechanical scaffold/list. See [docs/discussion.md](docs/discussion.md) for the design rationale.

### `autoland` — unattended commit-to-merge

Takes a change from working tree to merged PR with no human in the loop except for genuinely significant calls: commit, push, open a PR, make sure Copilot is requested as a reviewer, resolve review comments autonomously, watch CI and fix breaks, then merge the moment everything is green. Not model-invocable — trigger explicitly with `/autoland:autoland` (plugin commands are always namespaced by plugin name, so this can't be a bare `/autoland`) or "land this PR".

Self-contained: phase 3 (resolving review comments) uses its own bundled scripts under `skills/autoland/scripts/` (`fetch-comments.sh`, `list-threads.sh`, `reply-to-thread.sh`, `resolve-thread.sh` — resolving threads is GraphQL-only, handled by the script), no external skill dependency.

### `cleanup` — dry-run-then-confirm worktree tidying

Inventories development leftovers in the current worktree only — a merged branch (remote deletion; local branch and the worktree itself are never touched), per-worktree Docker containers, stale dev processes, implemented `plans/*.md` files, scratch/secrets files — then asks for confirmation via `AskUserQuestion` before deleting anything. Phase 1 is strictly read-only; nothing is applied without an explicit selection.

## Add a plugin

1. `mkdir -p plugins/<name>/.claude-plugin`
2. Write `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, `description`).
3. Add its components (`hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`). Use `${CLAUDE_PLUGIN_ROOT}` for paths inside the plugin.
4. Register it in `.claude-plugin/marketplace.json` under `plugins`.
