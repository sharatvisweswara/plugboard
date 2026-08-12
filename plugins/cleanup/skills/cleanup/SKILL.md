---
name: cleanup
description: Inventory development leftovers in the CURRENT worktree only — a merged branch (remote deletion, local left alone), per-worktree docker containers, stale dev processes, implemented plans/ files, scratch/secrets files — then ask the user for confirmation before deleting anything. Never removes the worktree itself, or its checked-out branch — that's the orchestrator/coordinator's job. Trigger on "clean up", "cleanup", "tidy up", "prune branches", "what can I delete".
---

# cleanup — dry run, confirm, apply (current worktree only)

Rules:
1. Scope is always the current worktree. Never enumerate, evaluate, or touch other worktrees, their branches, containers, or processes — that belongs to a cleanup run started from inside them, or to whatever coordinates worktrees across the box.
2. Phase 1 is strictly read-only. Nothing is deleted, stopped, or killed while inventorying.
3. Nothing is applied without explicit confirmation collected via AskUserQuestion. No exceptions, even for "obviously safe" items.
4. Never remove the worktree itself, and never delete the branch currently checked out in it. The two are inseparable — a checked-out branch can't be deleted, and this skill never removes the worktree to unblock that. Retiring a worktree is a decision for the orchestrator/coordinator operating at the box level, not for a cleanup run inside one of them.

## Phase 1 — Inventory (read-only, current worktree only)

Everything below is scoped to `pwd` (the current worktree). Do not run `orca worktree list` to cross-reference other worktrees, and do not treat other branches/containers/processes on the box as in scope — even something obviously safe to clean up belongs to a different worktree's own cleanup run, not this one.

1. **This worktree's branch.**
   - `git branch --show-current` to identify it; `git fetch origin main -q` (no `--prune`).
   - Check merge state: `git merge-base --is-ancestor <branch> origin/main`.
   - Check the remote still exists: `git ls-remote --heads origin <branch>`.
   - The **local** branch is never a deletion candidate here — it's checked out in this worktree, and this skill doesn't remove worktrees to unblock deleting it. If merged, report it as "ready for the coordinator to retire" and stop there.
   - The **remote** branch, if merged and owned by the current user (`git config user.name` / commit authorship), is an independent deletion candidate — deleting it doesn't require touching the local branch or the worktree.
2. **This worktree's cleanliness.** `git status --porcelain` for untracked non-ignored files and uncommitted changes. A dirty tree is reported, never a deletion candidate beyond the specific untracked files identified.
3. **Docker containers.** `docker ps -a`, filtered to names matching *this* worktree's directory name (e.g. `<worktree-dir-name>-db-1`) or the project's compose prefix for it. Containers belonging to any other worktree are out of scope — do not list them, not even as "unrecognized."
4. **Processes.** `pgrep -af 'stripe listen|vite|uvicorn|pnpm.*dev|diffity|stripe_listen'` (adapt to the project), filtered by `readlink /proc/<pid>/cwd` to only those rooted under the current worktree's path. A process rooted elsewhere is out of scope, not reported.
5. **Repo files.** `plans/*.md` in this worktree whose plan is implemented and merged (delete-after-merge convention — verify the plan's scope against merged code before proposing); stale `pre-rebase-backup-*` / `backup-*` branches only if relevant here (per rule 4, the current branch is report-only regardless — anything else is out of scope).
6. **Secrets-ish scratch.** Redirected secrets caches, `secrets.json` in this worktree's scratchpad. Propose deletion; never print contents.

## Phase 2 — Report and confirm

Present the dry run as a grouped report: category → items → the exact command that would run per item. Separate clearly:
- **Proposed** (verified safe: merged, clean, attributed to this worktree), with per-category counts.
- **Verify first** (ambiguous: unmerged commits, a dirty tree, unattributed processes) — each with the one command the user can run to decide. Do not bundle these into the apply.
- **Informational, not actionable**: this worktree's own retirement-readiness (branch merged + tree clean). State it plainly and note that retiring it is the coordinator's call, not something this skill offers to do.

Then AskUserQuestion, `multiSelect: true`, one option per non-empty *actionable* category (remote branch / containers / processes / files). Never include "worktree" or "local branch" as a selectable option — they are not actions this skill performs. Only what the user selects gets applied.

## Phase 3 — Apply (confirmed categories only)

- Remote branch: `git push origin --delete <branch>` — only the user's own, only merged.
- Containers: `docker stop && docker rm`. Volumes are NOT removed with the container; if dangling volumes exist afterward, report them and ask separately.
- Processes: `kill <pid>` (SIGTERM). Escalate to `-9` only if it survives and the user confirmed the kill.
- Files: plain `rm` for confirmed scratch/plan files.
- If git throws an `index.lock` error, wait a second and retry — never delete the lock file.
- Never run `orca worktree rm`, `git worktree remove`, or `git branch -d`/`-D` on the current worktree's own branch from this skill, under any confirmation. If the user wants the worktree retired, tell them that's a coordinator-level action, not something to do from inside it.

Finish with a done/skipped/failed summary per item.
