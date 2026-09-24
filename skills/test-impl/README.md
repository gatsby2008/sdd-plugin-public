# Test Implementation — Optional

Optional step in the **high-risk** flow. Implements the tests designed by `/sdd:test-design`, reading its artifact — and refuses to run without it. Skippable — you may go straight to `/sdd:commit`.

---

## Prerequisites

- Active pipeline (`.specwork/`) with implementation changes
- **`/sdd:test-design` completed** — its artifact at `.specwork/_test/<slug>-test-design.md` is required
- Implementation complete — class and component names must exist in source

---

## Usage

```bash
/sdd:test-impl             # auto-detects from current branch
/sdd:test-impl PROJ-15535 # explicit ticket ID
/sdd:test-impl list        # show planned files without writing
```

---

## What It Produces

| Stack | Unit tests | Integration tests | E2E |
|-------|-----------|-------------------|-----|
| Java | `*Test.java` (`@ExtendWith(MockitoExtension)`) | `*IntTest.java` / `*IT.java` — detected from `src/intTest/` layout (`@WebMvcTest` / `@DataJpaTest`) | — |
| Frontend | `*.test.ts` (Jest/Vitest + MSW) | `*.test.tsx` (RTL + MSW, full component tree) | Playwright/Cypress skeleton |

**Assertion quality**: tests must verify behavior, not absence of crashes. Before authoring, the skill reads each implementation file and extracts concrete return values, persistence calls, published events, and exception types — assertions then target those facts. Patterns like `assertThat(result).isNotNull()` or `verify(repo).save(any())` are treated as defects (allowed only as preconditions to a content check).

---

## Troubleshooting

**Generated tests miss obvious gaps**
Run `/sdd:test-design` in the same session first; its chat output gives this skill more context about what to cover.

**Generated test has wrong class/import names**
The skill scans existing test files for conventions. If the project has unusual
patterns, review generated imports before committing.

**E2E skeleton skipped**
No `e2e/` or `cypress/` directory was found. Create the directory structure first
if your project uses E2E tests, then re-run `/sdd:test-impl`.

---

## Next Step

```bash
/sdd:commit      # auto-stages the test files, then:
```

---

## Pipeline Position

```
/sdd:start
/sdd:implement → /sdd:commit   ← repeat per step
/sdd:test-design
/sdd:test-impl     ←  you are here
/sdd:code-review   (optional)
/sdd:mr
/sdd:mr-address
/sdd:close
```
