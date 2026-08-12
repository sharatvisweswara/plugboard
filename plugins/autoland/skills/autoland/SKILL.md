---
name: autoland
description: Commit, push, and open a PR, make sure Copilot is requested as a reviewer, autonomously address any review comments, then watch CI and fix anything that breaks, merging as soon as everything is green — no human approval requested. Not model-invocable; trigger explicitly with "/autoland" or "land this PR".
allowed-tools: Read, Edit, Write, Bash, Agent, AskUserQuestion
disable-model-invocation: true
---

# autoland

Take a change from working tree to merged PR with no human in the loop except
for genuinely significant calls. Five phases, run in order, looping back into
phase 3/4 whenever a push produces new review comments or new CI results.

1. **Commit, push, PR** — the usual flow.
2. **Copilot reviewer** — make sure it's actually requested.
3. **Resolve review comments** — autonomously; escalate only on significant
   decisions.
4. **Watch CI and fix breaks** — don't just wait, fix and keep going.
5. **Merge** — the moment everything is green, no approval requested.

---

## Phase 1: Commit, push, PR

Standard flow:

1. `git status` / `git diff HEAD` to see what's changed.
2. If on `main`/`master`, create a new branch.
3. Stage and commit with a message that follows this repo's commit
   conventions if a `CLAUDE.md` documents them (e.g. conventional commits);
   otherwise a plain, imperative, why-focused message. Split unrelated
   changes into separate commits.
4. `git push -u origin <branch>`.
5. `gh pr create` with a real title/summary/test-plan (see the repo's PR
   template if one exists).

Do this in one batch — there's nothing to decide yet.

## Phase 2: Make sure Copilot is on as a reviewer

Many orgs auto-request a Copilot review on every PR; don't assume it worked.

```bash
gh pr view --json reviewRequests,reviews --jq '.reviewRequests, .reviews'
```

If `copilot-pull-request-reviewer[bot]` (or whatever Copilot's reviewer login
is in this org) is not in `reviewRequests` and hasn't already left a review,
request it explicitly:

```bash
gh api repos/{owner}/{repo}/pulls/{pr}/requested_reviewers \
  -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

If that 422s, Copilot reviews likely aren't enabled for this repo at all —
note it and move on rather than retrying.

## Phase 3: Wait for and resolve review comments

Poll for Copilot's review to land (it can take a few minutes):

```bash
gh pr view --json reviews --jq '.reviews[] | select(.author.login | test("copilot"; "i"))'
```

Once it's posted (or any other reviewer left comments), reuse the
`resolve-pr-comments` skill's scripts directly rather than re-deriving this:

```bash
~/.claude/skills/resolve-pr-comments/fetch-comments.sh
~/.claude/skills/resolve-pr-comments/list-threads.sh
~/.claude/skills/resolve-pr-comments/reply-to-thread.sh COMMENT_ID "..."
~/.claude/skills/resolve-pr-comments/resolve-thread.sh THREAD_NODE_ID
```

**Deviation from that skill's default**: do not stop and wait for a plan
approval on every thread. For each open thread:

- If the fix is mechanical/unambiguous (style, an obvious bug, a naming nit,
  a missing null-check, a test gap Copilot flagged correctly) — apply it,
  commit, push, reply to the thread referencing what changed, resolve it.
  Proceed without asking.
- If the comment implies a decision with real weight — it contradicts an
  accepted ADR, changes a public API/contract, touches auth/security in a
  non-obvious way, requires a schema/migration choice, or Copilot's
  suggestion is itself debatable/contested — stop and ask the user via
  AskUserQuestion with the comment, your read of the tradeoff, and a
  recommendation. Don't guess on these.
- If a comment is flat wrong or not applicable, reply explaining why and
  resolve it — that's not a "significant decision," it's routine review
  hygiene.

Every push here can trigger a fresh Copilot review — after pushing fixes,
re-fetch comments before moving to phase 4, and loop phase 3 until there are
no unresolved actionable threads left.

## Phase 4: Watch CI and fix breaks

Do **not** use `monitor-and-merge.sh` as-is here — it exits on the first
failure instead of fixing it. Poll directly and react:

```bash
gh pr checks
```

Same build-vs-test distinction as `monitor-ci-and-merge`: a `build` check
passing does not mean tests passed — watch for the actual `test` check
(named something like `ci/circleci: test`), and don't treat its absence as
failure while `build` is still running.

On a **failed** check:

1. Pull the failure logs. If this repo's checks run on CircleCI, use the
   CircleCI MCP tools (`get_build_failure_logs`, `get_job_test_results`) —
   they're faster and more precise than scraping `gh run view`. Otherwise
   `gh run view --log-failed`.
2. Diagnose the root cause and fix it in the working tree.
3. Commit, push, and resume polling — don't exit the loop.
4. Track failures per check. If the **same** check fails again after a fix
   attempt, try once more; on a third consecutive failure of the same check,
   stop and escalate to the user with the failure detail rather than
   thrashing indefinitely.

Poll on an interval (e.g. every 30–60s via a backgrounded loop), not tight —
CI runs take minutes.

## Phase 5: Merge

Once every check is green (test check specifically passed, nothing pending)
and no unresolved review threads remain:

```bash
gh pr merge --merge || gh pr merge --rebase
```

Never `--squash`. No approval is requested before merging — that's the
point of this skill. If the merge itself is rejected by branch protection
(e.g. "review required"), that's a repo policy decision, not something to
bypass with `--admin` — stop and tell the user what blocked it instead of
forcing it through.

## Invariants

- Never squash-merge.
- Never force-bypass branch protection (`--admin`) to push a blocked merge
  through — surface it instead.
- Only interrupt the user for decisions with real weight (ADR conflicts,
  contract/schema changes, contested suggestions) — everything else,
  proceed autonomously.
- Re-check for new review comments after every push; re-check CI after every
  push. A push can invalidate both.
