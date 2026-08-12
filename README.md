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
```

## Plugins

### `comms` — communication styles

Features that shape *how Claude communicates* (response format, tone, register). Each feature toggles independently, and the whole plugin has a kill switch. Control it with the `/comms:style` command:

| Command | Effect |
| --- | --- |
| `/comms:style` or `/comms:style list` | list features + their on/off state |
| `/comms:style disable` | kill switch — turn the whole plugin off |
| `/comms:style enable` | turn the whole plugin back on |
| `/comms:style disable <feature>` | turn one feature off |
| `/comms:style enable <feature>` | turn one feature on |
| `/comms:summary` | one-off: dump current task status as an executive summary (verdict line + detail) |

`/comms:summary` is a plain command, not a toggleable feature — it runs once when invoked rather than shaping every reply.

Current features:

| Feature | Event | Group | What it does |
| --- | --- | --- | --- |
| `bullets` | UserPromptSubmit | `response-format` | Reply grouped into sections — ✅ Done, ℹ️ Info, ⚠️ Warning, 📋 Todo — with priority-tagged (🔴/🟡/🟢) todos. |
| `checklist` | UserPromptSubmit | `response-format` | Persistent checklist (`pending`/`in_progress`/`completed`/`blocked`), one `in_progress` at a time. |

> **Grouped features are opt-in (default OFF).** Members of a group are mutually exclusive — enabling one auto-disables its siblings — so the plugin never picks one for you. After installing or updating, no response-format behavior is active until you turn one on: `/comms:style enable bullets` (or `checklist`). Ungrouped features stay opt-out (default ON).

#### How the toggle infrastructure works

A single dispatcher (`hooks/dispatch.sh <Event>`) runs per hook event. It walks every feature, skips the disabled ones (and everything when the kill switch is on), collects each enabled feature's text, and emits one hook JSON envelope. State lives outside the plugin at `${CLAUDE_CONFIG_DIR:-~/.claude}/comms/` so it survives reinstalls:

- `plugin-disabled` present → kill switch on (whole plugin off)
- ungrouped feature (no `FEATURE_GROUP`) → default ON; `disabled/<id>` present turns it off
- grouped feature (`FEATURE_GROUP` set) → default OFF; `enabled/<id>` present turns it on, and at most one member of a group runs (enforced at read-time)

`scripts/comms-ctl.sh` is the one place that reads/writes this state; `lib/comms.sh` is the shared helper both it and the dispatcher source. A feature opts into mutual exclusivity by declaring `FEATURE_GROUP="<name>"` — siblings sharing that name are mutually exclusive, no CLI changes needed.

#### Add a feature to `comms`

1. `mkdir plugins/comms/features/<id>`
2. Write `features/<id>/feature.sh` declaring `FEATURE_NAME`, `FEATURE_DESC`, `FEATURE_EVENT`, and a `feature_run()` that prints the contribution. No side effects at source time.
3. If its `FEATURE_EVENT` is one the dispatcher isn't wired for yet, add one line to `hooks/hooks.json` pointing that event at `dispatch.sh <Event>`.

It's then auto-listed and auto-toggleable — no other wiring.

### `slog` — long-horizon work through a living document

For work too big for one exchange, `/slog` drives everything through a single markdown doc per feature (`docs/work/<slug>.md`) instead of chat back-and-forth. The doc holds the goal, a Definition of Done whose criteria each declare their evidence type, open questions, diagrams-first design, an append-only decisions log, and a task checklist. The agent works the doc, records evidence inline, and auto-advances status (`draft → agreed → building → done`) as each gate is met — surfacing to chat only for blocking questions, sign-off, or the done-gate.

| Command | Effect |
| --- | --- |
| `/slog:start <slug>` | scaffold `docs/work/<slug>.md` from the template, status `draft` |
| `/slog:resume` | resume the active doc — report status + next actionable item |
| `/slog:list` | list docs under `docs/work/` with their status |

slog is a command-only plugin — no hooks, no toggles. Each command inlines the shared protocol from `slog/protocol.md`; `scripts/slog.sh` only does the mechanical scaffold/list. See [docs/discussion.md](docs/discussion.md) for the design rationale.

## Add a plugin

1. `mkdir -p plugins/<name>/.claude-plugin`
2. Write `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, `description`).
3. Add its components (`hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`). Use `${CLAUDE_PLUGIN_ROOT}` for paths inside the plugin.
4. Register it in `.claude-plugin/marketplace.json` under `plugins`.
