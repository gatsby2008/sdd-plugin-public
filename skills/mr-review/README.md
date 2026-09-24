# Peer Review

One-step stack-aware review of **someone else's** branch or merge request. Give it
a branch name or an MR link and it produces a compact prioritized report — without
ever checking out the branch or touching your working tree.

Answers: *is this peer's change safe and well-built?*

> Companion to `/sdd:code-review`. That skill reviews your own uncommitted work;
> `/sdd:mr-review` reviews committed work that belongs to someone else, resolved
> from a branch or MR. Both share the same review engine (stack routing, test
> coverage check, pack hints, report format).

---

## Prerequisites

- For GitHub PR links/IIDs: `gh` installed and authenticated (`gh auth status`).
- For GitLab MR links/IIDs: `glab` installed and authenticated (`glab auth status`).
- For branch names: the branch exists on `origin` (no CLI needed — uses `git`).
- Reviewer agents for the stack you're reviewing:
  - Java → `sdd:java:quality-reviewer`, `sdd:java:security-reviewer`
  - Frontend → `sdd:ui:quality-reviewer`, `sdd:ui:a11y-reviewer`

---

## Usage

```bash
/sdd:mr-review feature/PROJ-15518                                  # a peer's branch
/sdd:mr-review https://gitlab.com/grp/proj/-/merge_requests/123     # a GitLab MR link
/sdd:mr-review https://github.com/owner/repo/pull/123               # a GitHub PR link
/sdd:mr-review 123                                                  # an MR/PR IID
```

---

## What It Does

1. Figures out whether you passed a branch, a GitLab MR link, a GitHub PR link, or a numeric IID.
2. Resolves it to the same diff a reviewer sees:
   - GitHub PRs via `gh pr diff` (merge-base based).
   - GitLab MRs via `glab mr diff` (merge-base based).
   - Branches via `git diff origin/<target>...origin/<branch>`.
3. Runs the stack-aware review engine on that diff — the same one `/sdd:code-review`
   uses (quality + security review, advisory test-coverage gaps, pack hints).
4. Writes a local report and prints it.

It never checks out the branch, switches your branch, or modifies anything. Your
working tree is exactly as you left it.

---

## When to Use

- A teammate asks you to review their MR and you'd rather not juggle `git fetch`
  commands to feed it to `/sdd:code-review`.
- You want a second opinion on an MR before approving, without leaving your branch.
- You received a branch name (not an MR) and want a review before it opens.

---

## Output / Next Step

Writes the report to:

- `.specwork/_review/<slug>-peer-review.md` if a pipeline workspace exists, or
- `~/.claude/peer-reviews/<slug>-<date>.md` otherwise (path printed on completion),

and prints the full report. Sections: verdict, summary, test-coverage gaps,
security findings, quality findings, action plan, questions, suggested follow-ups.

This is read-only — it does not apply fixes and does not comment on the MR. Take
the findings into your MR review by hand.

---

## Troubleshooting

**`gh` / `glab` not installed or not authenticated**
Run `gh auth login` (GitHub) or `glab auth login` (GitLab), or pass the branch
name instead — branch mode needs only `git`.

**Nothing to review**
The diff between the base and the branch/PR is empty. Check you passed the right
branch, or that the PR still has open changes.

**Wrong base branch**
Branch mode defaults to `main`. Pass the branch name explicitly if your repo merges into a different base (e.g. `/sdd:mr-review feature/foo` against `development` — use the branch form and the base will be auto-detected from the common default).

**Agents missing**
The reviewers ship with the sdd plugin — make sure it's installed and enabled
(`/plugin install sdd@gatsby`).

---

## Related Skills

- `/sdd:code-review` — reviews your own working-tree diff (shared engine)
- `/sdd:mr-address` — for the author, after the MR opens
