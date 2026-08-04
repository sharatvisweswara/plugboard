# Survey: response-format conventions

Comparison feeding [research-response-formats.md](research-response-formats.md).

## AI coding agents

| Tool | Convention |
|------|------------|
| Aider | No built-in fixed prefix/status tags. Style is steered via a `CONVENTIONS.md`/`AGENTS.md` file the user writes and includes in context — the convention is user-authored prose, not a tool-imposed tag set. |
| Cursor | Similar: rule files (`.mdc`, numeric-prefixed like `001-style.mdc`) hold persistent style instructions rather than the agent stamping a fixed status tag on every reply. |
| Cline | Maintains an explicit todo list with a status enum: `pending` / `in_progress` / `completed`, merged across turns by `id` rather than restated each time. Convention enforces exactly one `in_progress` item at a time. |
| GitHub Copilot CLI / Workspace | Plan-then-execute structure (a plan section, then commit-style output) rather than a per-line status prefix. |

Takeaway: most agent tools don't force a fixed bracket-tag vocabulary on every reply. Where they do track status (Cline), it's a persistent state machine (pending/in_progress/completed) merged turn-over-turn, not a repeated-every-line prefix like this plugin's current `[DONE]/[TODO]/[INFO]/[WARN]`.

## General software / logging conventions

| Convention | Shape |
|------------|-------|
| Conventional Commits | `type(scope)!: description` — a single required type prefix per unit (commit), not per line, drawn from a small closed vocabulary (`feat`, `fix`, ...). Requirement language defined via RFC 2119. |
| RFC 2119 keywords | `MUST`/`SHOULD`/`MAY` etc. express normative strength, not status — a different axis (obligation) than the plugin's status axis (done/pending/info/warning). Not a direct substitute. |
| syslog severity (RFC 5424) | 8 fixed severity levels (`emerg`...`debug`), one per message, chosen from a closed enum — structurally close to the current `[DONE]/[TODO]/[WARN]/[INFO]` tag approach, just with more levels and a different vocabulary. |

Takeaway: syslog-style severity tagging validates the plugin's existing approach (closed vocabulary, one tag per unit). The genuinely different alternative is the Cline-style persistent checklist: state lives across turns instead of being restated as tagged bullets every reply.

## Recommendation

Build the checklist convention as a second, mutually-exclusive format (implemented as `response-format-checklist`) since it's a structurally distinct alternative backed by real precedent (Cline), rather than a cosmetic variant of the existing tag set (which syslog/conventional-commits would just be a reskin of).
