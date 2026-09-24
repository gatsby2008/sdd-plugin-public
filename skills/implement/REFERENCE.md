# implement — Reference

Reference material for `/sdd:implement`. Decision tables, output templates, and persistent escalation format. `SKILL.md` is the execution flow; this file holds the structures and templates.

---

## Failure decision matrix

Used in Step 6 to classify a test or validation failure before attempting a fix:

| Failure type | Signals | Action |
| --- | --- | --- |
| Direct implementation error | assertion mismatch tied to changed behavior, wrong return value, missing field, wrong mapping, compile error in modified file | Attempt focused fix |
| Related test setup error | test fixture missing new required field, mock not updated for changed method signature, expected payload outdated because behavior intentionally changed | Attempt focused fix |
| Existing unrelated failure | failing test does not touch modified files or changed behavior | Escalate immediately |
| Spring context / infrastructure failure | `ApplicationContext` fails, bean wiring unclear, profile/config issue, datasource/Testcontainers issue, port/env problem | Escalate unless clearly caused by this change |
| Environmental/flaky failure | timeout, network, Docker/Testcontainers instability, random ordering, non-deterministic failure | Escalate immediately |
| Business ambiguity | expected behavior unclear, assertion could be valid under multiple interpretations | Stop and create/update Open Question |

---

## Escalation entry format

Used in Step 6 when persisting an escalation to `.specwork/_progress/escalations.md`. Append one block per escalation:

```markdown
## <YYYY-MM-DD> — <one-line summary, e.g. "Integration test escalation">

Failing area:
<test/component/subsystem>

Error excerpt:
<short excerpt — keep it tight, no full stack traces>

Suspected root cause:
<summary>

Files modified:
- <file>
- <file>

Fixes attempted:
- <attempt 1>
- <attempt 2>

Recommended human review:
<file/config/test setup>
```

---

## Risk classification table

Used in Step 8 to assign a final risk level. Risk is not determined by file count alone — one async change in a single class may be HIGH; dozens of DTO changes may still be LOW.

| Risk Signal | Description | Risk Level | Recommend test-design |
| --- | --- | --- | --- |
| DTO changes only | Simple request/response field changes without logic | LOW | No |
| Mapper adjustments | MapStruct/manual mapping updates without business logic | LOW | No |
| Validation message changes | Minor validation or error message updates | LOW | No |
| CRUD isolated change | Simple repository/service CRUD behavior | LOW | No |
| Existing tests already cover behavior | High confidence in current coverage | LOW | No |
| Single service method modification | Business logic changed in one bounded area | MEDIUM | Usually No |
| Multiple repositories affected | Change spans several persistence operations | MEDIUM | Maybe |
| Business rule modifications | Logic affecting calculations/decision paths | MEDIUM | Maybe |
| Controller + Service + Repository touched | Cross-layer impact detected | MEDIUM | Maybe |
| Existing tests require updates in multiple areas | Regression surface increasing | MEDIUM | Maybe |
| Async processing detected | CompletableFuture, ExecutorService, @Async, threads | HIGH | Yes |
| Event-driven flow modified | SNS/SQS/Kafka/event consumers/producers touched | HIGH | Yes |
| Retry logic changed | RetryTemplate, retry policies, backoff logic | HIGH | Yes |
| Transactional boundaries modified | @Transactional behavior or transaction flow changes | HIGH | Yes |
| Integration-test-sensitive flow | Multiple services/components interact | HIGH | Yes |
| Distributed side effects possible | External APIs/events/state propagation | HIGH | Yes |
| Concurrency-sensitive logic | Shared state, locks, synchronization, race conditions | HIGH | Yes |
| Critical business flow impacted | Consent, payments, lead creation, approvals, etc. | HIGH | Yes |
| Weak or missing test coverage detected | Low confidence in regression protection | HIGH | Yes |
| Unclear regression surface | Difficult to predict affected areas | HIGH | Yes |

## Recommendation logic

| Final Risk Level | Recommended Next Phase |
| --- | --- |
| LOW | `/sdd:commit` |
| MEDIUM | `/sdd:commit` (optionally `/sdd:test-design` first) |
| HIGH | `/sdd:test-design` |

The recommendation is advisory **to the developer** — they may skip any step — but the printed next phase must match the assigned risk level. Do not substitute a lower phase.

**HIGH does not downgrade because inline tests exist.** `/sdd:test-design` scans the tests already written during `/sdd:implement` and designs **only the missing cases** (real concurrency/race coverage, migration idempotency, untested edge cases) — it never duplicates them. Existing inline coverage is a reason to *run* test-design (to find its gaps), not to skip it.

When more implementation steps remain before the feature is complete, recommend `/sdd:implement` instead.

---

## Output templates

Used in Step 8 to print the final summary. Pick the block matching the assigned risk level (or the escalation block if Step 6 escalation triggered).

**Normal completion — HIGH risk:**

```text
Implementation completed.
Risk assessment: HIGH
- <observed signal, e.g. async/event-driven changes detected>
- <observed signal, e.g. transactional boundaries modified>
- <observed signal, e.g. weak test coverage detected>

Recommended next phase:
/sdd:test-design
```

**Normal completion — MEDIUM risk:**

```text
Implementation completed.
Risk assessment: MEDIUM
- <observed signal, e.g. multiple repositories affected>
- <observed signal, e.g. cross-layer change detected>

Recommended next phase:
/sdd:commit

Optional: run /sdd:test-design first if you want targeted test coverage before committing.
```

**Normal completion — LOW risk:**

```text
Implementation completed.
Risk assessment: LOW
<One sentence describing why scope is simple, e.g. "Change limited to DTO and mapper adjustments.">

Recommended next phase:
/sdd:commit
```

**Escalation triggered:**

```text
Escalation required.

Failing area:
  <test/component/subsystem>

Error excerpt:
  <short excerpt>

Suspected root cause:
  <summary>

Files modified:
  <files>

Fixes attempted:
  <list>

Recommended human review area:
  <file/config/test setup>

Review the reported failing area manually before continuing.
After fixing manually, rerun the focused test or continue with:
/sdd:implement
```

Do not hide failed tests behind a normal "done" message.
