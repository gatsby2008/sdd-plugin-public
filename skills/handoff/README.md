# Handoff

Build a **curated execution capsule** from existing SDD artifacts so another coding
agent (Gemini, Copilot, Codex, or Claude) can pick up the feature without re-analyzing it.

`/sdd:handoff` is not a documentation export. It packages a compact, opinionated pack
that puts a dense execution summary first and pushes the full spec to the bottom,
because most executor models degrade with long preambles.

---

## Prerequisites

- Active pipeline branch with `.specwork/_state/<slug>-state.json`
- All required artifacts must exist:
  - `.specwork/_state/<slug>-state.json`
  - `.specwork/_state/<slug>-rules.json`
  - `.specwork/_spec/<slug>-spec.md`
- All Open Questions resolved (verified via `gates.py check-oqs`) — same gate as `/sdd:implement`

Optional artifacts (consumed when present, omitted gracefully when not):

- `.specwork/_plan/<slug>-plan.md` — fills the *Target Files* and *Plan* sections (when `/sdd:plan` was run)
- `.specwork/_state/<slug>-implementation-cache.json` — fills the *Known Architecture Context* section
- `.specwork/_progress/<slug>-context.md` — fills the *Focused Context* section
- `.specwork/_progress/escalations.md` — fills the *Known Blockers / Escalations* section (auto-written by `/sdd:implement` when its Escalation Policy triggers)

If any required artifact is missing, `/sdd:handoff` exits cleanly without making changes.

---

## Usage

```bash
# Auto-detect slug from current branch
/sdd:handoff

# Explicit slug (if needed)
/sdd:handoff my-feature-123
```

---

## What It Produces

**Markdown execution capsule** (for pasting into another agent):

```text
.specwork/_handoff/<slug>-execution-pack.md
```

**Machine-readable summary** (for tracking which optional sections were included):

```text
.specwork/_handoff/<slug>-execution-pack.json
```

---

## Execution Pack Structure

Ordered for the executor's attention budget — densest info first, embedded artifacts last:

1. **Role** — short identity and behavior instructions
2. **Execution Summary** — Goal, Primary class/service, Main behavior (extracted from spec)
3. **Behavioral Change Warning** — *conditional* — surfaced near the top when the spec/plan signals modifications to existing behavior (keywords like "idempotent", "no-op", "no longer", or `[infra]` / `[reference-update]` tags in plan)
4. **Known Architecture Context** — repositories, primary classes, patterns, related tests from `implementation-cache.json` (or a "first run" notice if empty)
5. **Target Files** — verbatim from `plan.md`'s `## Target Files` table (omitted if no plan)
6. **Expected Change Scope** — verbatim from the spec's `## Expected Change Scope` section
7. **Safe Constraints** — verbatim from the spec's `## Safe Constraints` section
8. **Service Rules** — global + service rules from `rules.json`
9. **Execution Budget** — fixed boilerplate (avoid scans, prefer focused diffs)
10. **Failure Handling** — fixed retry/escalation policy
11. **Complexity Indicators** — yes/no flags from spec keywords (concurrency / integration scope)
12. **Plan** — full plan body minus `## Target Files` (omitted if no plan)
13. **Spec** — full spec, minus the sections already extracted above
14. **Focused Context** — `_progress/<slug>-context.md` if present
15. **Known Blockers / Escalations** — `_progress/escalations.md` if present (prevents the executor from repeating failed attempts)
16. **Expected Response From Executor** — what the pack expects back
17. **Stop Conditions** — when the executor must halt (includes the Target Files contract: any file outside the table that isn't in plan's Out-of-Plan list is a stop)

---

## No-Enrichment Rule

`/sdd:handoff` may curate, reorder, summarize, and mechanically derive sections from existing
`.specwork` artifacts. It must **not** introduce new business meaning, new implementation
decisions, new file targets, new constraints, or new assumptions.

Every derived section is traceable to one of: `spec.md`, `plan.md`, `rules.json`,
`implementation-cache.json`, `context.md`, `escalations.md`. If the source isn't present, the section is omitted.

The `Execution Budget` and `Failure Handling` sections are exempt — they are fixed
boilerplate declared in the skill itself.

---

## When to Use

**Hand off to another agent:**
```bash
/sdd:start      # initialize branch/state/source
/sdd:spec       # draft the spec from the source
/sdd:handoff    # build the execution capsule
# ... paste pack into Gemini / Copilot / Claude ...
```

**Continue locally** (no handoff needed):
```bash
/sdd:start
/sdd:implement
/sdd:commit
/sdd:mr
```

---

## Hard Rules

- Does not scan the repository for new content. Bounded `test -e` checks against paths named in `plan.md` Target Files are allowed (Step 4.5 freshness gate).
- Does not enrich the spec — verbatim extraction or mechanical derivation only.
- Does not generate implementation details or resolve Open Questions.
- Does not read AGENTS.md or service-rules.md directly.
- Uses only `.specwork` artifacts plus the bounded path checks above.
- Missing required artifacts = clean exit (no writes).
- Worktree diverging from `plan.md` Target Files = clean exit asking for `/sdd:plan` re-run (no writes).

---

## Typical Handoff Flow

```
Alice (Claude):                Bob (Gemini or Copilot):
  /sdd:start          ────────→  reads execution capsule
  /sdd:handoff        ────────→  implements code
                    ────────→  runs tests
                    ←────────  returns files + summary
  /sdd:commit                    (paste Bob's diff)
  /sdd:mr
```

---

## Troubleshooting

**"No handoff generated. Missing required artifacts."**
Run `/sdd:start` first.

**"No handoff generated. Unresolved Open Questions."**
Resolve all `- [ ]` items in the `## Open Questions` section of `.specwork/_spec/<slug>-spec.md` **and** `.specwork/_plan/<slug>-plan.md` (when plan exists) before creating a handoff. Spec OQ = business behavior ambiguity; plan OQ = discovery/implementation-path ambiguity. Checkboxes elsewhere in either file are ignored.

**"Worktree diverges from plan — pack not generated."**
The plan was created when the worktree looked different. A file marked `(new)` already exists, or a file the plan expected to modify is no longer there. Re-run `/sdd:plan` to regenerate Target Files against the current worktree, then re-run `/sdd:handoff`. (Validated by `gates.py worktree-freshness`.)

**"Handoff pack created."**
Success. Copy `.specwork/_handoff/<slug>-execution-pack.md` and paste into your executor. If a `## Behavioral Change Warning` section appears near the top, the spec implies modifications to existing code paths — surface that to the executor explicitly.

---

## Next Steps

After handoff:
- Paste the execution capsule into your executor model's chat
- Executor implements and returns the items listed under *Expected Response From Executor*
- You paste the diff back and run `/sdd:commit`, `/sdd:mr`

---

## Related Skills

- `start` — creates the state, rules, source, and spec (now with Expected Change Scope + Safe Constraints sections)
- `implement` — implement locally instead of handing off
- `commit` — commit the returned changes
