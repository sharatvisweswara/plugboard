---
description: Dump current task status as an executive summary
allowed-tools: Bash(sh:*), Bash(git:*)
---

Report the current state of work as an executive summary: one line at the top stating the verdict (done / in progress / blocked, and on what), then a few lines of supporting detail underneath (what's done, what's left, any blockers). No preamble, no restating this instruction.

Ground the summary in real state, don't invent progress:

Working tree:
!`git status --short`

Draw the rest from the conversation's own task/todo state. If this work has an active `docs/work/<slug>.md` slog doc, note its status and point at `/slog:resume` rather than re-deriving it here. If nothing is in progress, say so in the verdict line.
