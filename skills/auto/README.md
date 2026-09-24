# Auto Pilot

One command to drive the whole SDD pipeline for a ticket or description. Chains
`/sdd:start → /sdd:spec → /sdd:plan → /sdd:implement → /sdd:commit → /sdd:mr`, asks
for branch confirmation in `/sdd:start`, then stops once the MR is open.

> For trivial and focused work the pipeline is deterministic, so firing each step
> by hand is busywork. `/sdd:auto` runs the sequence and pauses only when a human
> decision is actually required.

---

## Usage

```bash
/sdd:auto PROJ-15535                          # a Jira ticket
/sdd:auto "add a /health endpoint to the API"  # a free-text description
```

---

## What It Does

1. Pipeline entry:
   - **No pipeline + a ticket/description:** runs `/sdd:start` (**with branch
     choice A/B/C**).
   - **No pipeline + no argument:** **stops hard** — there is nothing to start
     from, so it never creates a branch or `.specwork/` from empty input.
   - **Pipeline already exists + same work** (no argument, or a ticket key that
     matches the active one): skips `/sdd:start` and continues on the current
     branch/artifacts.
   - **Pipeline already exists + different work** (a different ticket, or any
     free-text description): **stops hard** and tells you to `/sdd:pause` or
     `/sdd:close` the active pipeline first — it never specs over in-progress work.

   Then runs `/sdd:spec`, `/sdd:plan`, and `/sdd:implement` (repeated until every
   target is done).
2. **Stops hard** if the spec still has unresolved Open Questions after drafting
   — it will not guess past them. Resolve them and re-run.
3. Runs `/sdd:commit` (test-coverage gate + semantic commit), which in
   non-interactive mode continues automatically to `/sdd:mr`, then **stops**. It
   never runs `/sdd:close` (post-merge) or `/sdd:mr-address` (needs review
   comments that do not exist yet).
4. In non-interactive mode it continues automatically between steps; outside the
   Open Questions gate, it does not ask for extra confirmation.

---

## Gates & Pauses

| Pause | When | Behavior |
|------|------|----------|
| Branch choice | in `/sdd:start` | pick the working branch (A/B/C) |
| Open Questions | after `/sdd:spec` | **hard stop** — resolve, then re-run |

There is no pause at commit: after `/sdd:implement`, auto runs `/sdd:commit` →
`/sdd:mr` and then stops before `/sdd:close`.

---

## When to Use

- Trivial / focused tickets where the pipeline is deterministic end-to-end.
- You want the spec, plan, implementation, commit, and MR done unattended, then
  to take over for review and merge.

When **not** to use:
- Large or ambiguous features you want to shape step by step — drive the skills
  individually.
- Work you intend to hand to another agent — use `/sdd:handoff`.

---

## Output / Next Step

Auto mode runs through commit and opens/updates the MR, then stops. You take over
for review, merge, and `/sdd:close` after merge.

---

## Troubleshooting

**Stopped on Open Questions**
Auto mode won't guess. Resolve the OQs in the spec (e.g. `/sdd:spec` with the
answers as context), then re-run `/sdd:auto` or continue with `/sdd:plan`.

**It stopped at the MR and didn't close the branch**
By design — closing is a post-merge human decision. Run `/sdd:close` yourself after
the MR merges.

---

## Related Skills

- `/sdd:start`, `/sdd:spec`, `/sdd:plan`, `/sdd:implement`, `/sdd:commit`, `/sdd:mr` — the chained steps
- `/sdd:test-design`, `/sdd:test-impl` — optional; run them by hand before `/sdd:auto` if the change warrants tests
- `/sdd:handoff` — delegate execution to another agent instead of driving it here
