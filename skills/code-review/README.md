# Code Review

Runs stack-aware quality/security review on the current branch diff.
Produces a compact prioritized report and waits for approval before any fixes.

Answers: did we build it well?

> Evolved from the original `/java-review` and `/ui-review` vibe-coding commands.
> Those were two narrow tools — one per stack — that this skill consolidates into
> a single stack-aware entry point, adds persistence to `.specwork/_review/` for
> pipeline use, and gains a `--recheck` mode for comparing against a previous report.

---

## Usage

```bash
/sdd:code-review
/sdd:code-review --recheck
```

- normal mode: first-pass review
- recheck mode: compare current diff vs previous findings

---

## Preconditions

- active pipeline branch, or any current branch when reviewing outside SDD
- at least one staged or unstaged change
- required agents installed for detected stack

---

## Stack Routing

- Java (`build.gradle` / `pom.xml`): `sdd:java:quality-reviewer` + `sdd:java:security-reviewer`
- Frontend (`package.json`): `sdd:ui:quality-reviewer` + `sdd:ui:a11y-reviewer`
- Ambiguous stack: pick by changed files and flag ambiguity

---

## Output

Writes:

```text
.specwork/_review/<id>-code-review.md
```

Report sections:
- verdict: `PASS` / `PASS WITH WARNINGS` / `FAIL`
- summary (short)
- test coverage gaps (advisory — production classes in the diff whose test files were not touched; omitted when none)
- security findings
- quality findings
- action plan
- questions/uncertainties
- suggested follow-ups (advisory — surfaces deeper opt-in packs when the diff touches JPA, async/concurrency, REST controllers, or logging; omitted when no triggers fire)

`--recheck` focuses on resolved, still-open, and new findings.

---

## Suggested Follow-ups

The review never loads the deeper packs into the reviewer agents — that would inflate the per-run token cost. Instead, when the diff hits a known area, the report points at a standalone pack the user can invoke manually:

| Area in diff | Suggested pack |
|---|---|
| `@Entity` / `@Repository` / `@Query` / `@Transactional` | `/sdd:jpa-patterns` |
| `@Async` / `CompletableFuture` / `synchronized` / virtual threads | `/sdd:concurrency-review` |
| New `@RestController` / `@*Mapping` | `/sdd:api-contract-review` |
| New logging calls / `MDC` / Feign client config | `/sdd:logging-patterns` |

The packs ship with the sdd plugin. The hints are advisory and do not change the verdict.

---

## Rules

- do not edit files before user approval
- review only code in the diff
- keep findings specific, minimal, and severity-ranked

---

## Troubleshooting

**Nothing to review**
No diff found.

**Agents missing**
The reviewers ship with the sdd plugin — make sure it's installed and enabled
(`/plugin install sdd@gatsby`).

## Related Skills

- `/sdd:mr` — open MR after reviews
