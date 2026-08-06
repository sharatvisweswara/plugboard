# slog protocol

Long-horizon work is driven through one living markdown document per feature, not through chat. The document is the single source of truth. You update it as a byproduct of doing the work — never as a separate ceremony.

## The document

Sections and conventions are defined in the template. Mandatory: Meta, Goal, Definition of Done, Tasks. The others are optional — delete a section rather than leaving it empty. Delete the guidance comments as you fill each section.

- **Definition of Done** is the acceptance gate. Each criterion declares its evidence *type* (pointer / test / screenshot / command) when the doc reaches `agreed`, and carries the actual evidence when met.
- **Tasks** is a plain checklist — the work breakdown. Tick items freely. Evidence lives in the DoD table, not here.
- **Design** is diagrams-first. Reach for mermaid when the thing is a structure or sequence (data model, flow, states, interaction). Use prose only for rationale or constraints a diagram can't carry. Never diagram a plain list.
- **Decisions** is append-only: choice + a one-line why, so settled points don't get re-litigated.

## Per-turn loop

1. Read the doc.
2. Reconcile it with reality (code, tests, files) — fix anything stale.
3. Advance the next actionable item.
4. Record evidence inline in the DoD as criteria are met; tick tasks as they complete.
5. Decide whether to surface to chat (see below); otherwise continue the loop.

## Status — you advance it automatically when the gate is satisfied

- `draft → agreed`: every **blocking** open question is answered and the DoD is accepted. (This gate depends on the user's answers; advance the moment they're in — don't ask for permission to advance.)
- `agreed → building`: no gate, just begin.
- `building → done`: every DoD criterion has evidence and all tasks are ticked.
- `done`: the doc commits alongside the code in the same PR, then the work is merged.

## Surface to chat ONLY when

- a **blocking** open question needs the user (a genuine fork: irreversible, a preference, or an ambiguous requirement — never a lookup you can resolve yourself),
- a decision needs the user's sign-off,
- the done-gate is reached.

Otherwise stay in the document. Keep chat messages short and point at the doc.

Keep the process light. If a rule here would cost more than it's worth for this particular piece of work, note that in the doc and move on — the goal is finished, evidenced work, not paperwork.
