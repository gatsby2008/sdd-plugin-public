# Test Design — Optional

Optional step in the **high-risk** flow. Runs inside an active pipeline (after `/sdd:implement`) and writes a design artifact (`.specwork/_test/<slug>-test-design.md`) that `/sdd:test-impl` consumes. Skippable — you may go straight to `/sdd:commit`.

---

## Prerequisites

- Active pipeline branch with `.specwork/_state/<slug>-state.json`
- **At least one code file changed** outside `.specwork/` — implementation must exist
- Spec file exists at `.specwork/_spec/<slug>-spec.md`

---

## Usage

```bash
/sdd:test-design
```

---

## What It Produces

A structured analysis printed in chat — test case design grouped by category (unit / integration / edge cases / missing coverage) with concrete class/component names extracted from the diff. The output is not persisted to disk; it is intended to be consumed in the same session, either as input to `/sdd:test-impl` or as a checklist for manual test authoring.

**Required coverage**: every design output must include at least one integration-level scenario per touched endpoint, listener, scheduled job, or top-level component. If the diff has no plausible integration entry point (pure helper, isolated library code), the output must call this out under *Missing Coverage* — silently omitting integration tests is treated as a defect.

Stack-specific structure:

| Java Spring Boot | Frontend |
|---|---|
| Unit / Integration / Edge Cases | Unit / Component / E2E |
| JUnit + Mockito | Jest/Vitest + RTL/Vue Test Utils + Playwright |
| Real class names from diff | Real component/hook names from diff |

---

## Troubleshooting

**"No implementation found on branch"**
The skill only runs after there are real code changes. Run `/sdd:implement` first,
then re-run `/sdd:test-design`.

**Missing Coverage section has items**
These are gaps that need infrastructure (e.g. LocalStack for SQS, Playwright setup)
or product clarification. Do not ignore them — resolve before closing the MR.

---

## Next Step

```bash
/sdd:test-impl
```

---

## Pipeline Position

```
/sdd:start
/sdd:implement → /sdd:commit   ← repeat per step
/sdd:test-design   ←  you are here
/sdd:test-impl
/sdd:code-review   (optional)
/sdd:mr
/sdd:mr-address
/sdd:close
```
