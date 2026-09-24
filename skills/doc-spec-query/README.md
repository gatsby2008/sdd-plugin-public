# Spec Query

Answers feature/spec questions by reading every published spec under
`~/.claude/spec-registry/*/` and synthesizing an answer from the combined
knowledge. The registry is populated by `/sdd:mr` (via `spec-publish.sh`) each time
a feature with a `.specwork` spec is merged.

## Usage

```bash
/sdd:doc-spec-query what does the lead-dedupe feature do?
/sdd:doc-spec-query which specs touch LeadProcessor?
/sdd:doc-spec-query which specs still have unresolved open questions?
/sdd:doc-spec-query what safe constraints apply to consent changes?
```

Pass any free-text spec/feature question as the argument.

## Example queries

### Feature lookup — what does a feature do?

```bash
/sdd:doc-spec-query what does the lead-dedupe feature do?
/sdd:doc-spec-query summarize the DataVendor retry feature in consumer-portal
```

### Impact / target scan — which specs touch X?

```bash
/sdd:doc-spec-query which specs touch LeadProcessor?
/sdd:doc-spec-query which features change the consent flow?
/sdd:doc-spec-query find specs that modify the SNS publisher
```

### Constraint search — which features carry which invariants?

```bash
/sdd:doc-spec-query which specs require idempotency?
/sdd:doc-spec-query which features forbid a schema change?
/sdd:doc-spec-query which specs mention PII handling?
```

### Open-Questions filter — what is still unresolved?

```bash
/sdd:doc-spec-query which specs still have unresolved open questions?
/sdd:doc-spec-query list every spec with open questions per service
```

### Acceptance criteria

```bash
/sdd:doc-spec-query what is the acceptance criteria for the lead-dedupe feature?
```

Every answer cites the source as `<service>/<spec-file>` — if a fact is stale,
the spec is refreshed the next time that feature flows through `/sdd:mr`.

## What it does

1. Lists every service subdir under `~/.claude/spec-registry/`.
2. **Detects whether the question targets a specific service** — matches kebab-case
   tokens in the query against the registry's subdir names, narrowing the read
   scope when one is found. Aggregate questions ("which services…", "compare",
   "across services") always trigger a full read.
3. Reads the specs in scope.
4. Synthesizes an evidence-based answer from their canonical sections (Summary,
   Behavior, Scope, Implementation Context, Safe Constraints, Open Questions),
   citing each claim with `<service>/<spec-file>`.

## Registry location

Defaults to `~/.claude/spec-registry/`. Override with `CLAUDE_DOC_HOME` to point at
a different folder (e.g., a cloned GitLab repo for team sharing) — the skill reads
from `$CLAUDE_DOC_HOME/spec-registry/`. The same variable governs the catalog and
ADR registries, so they all move together.

## Requirements

- At least one spec must exist under `~/.claude/spec-registry/*/`. Specs are
  published automatically by `/sdd:mr`; there is no separate publish step to run.

## Limitations

- Answers are only as fresh as the most recent `/sdd:mr` publish per feature.
- The skill never edits specs — it only reads them.

## Related Skills

- `/sdd:doc-spec` — stores a hand-written / standalone spec in the registry this skill reads.
- `/sdd:spec` (sdd bundle) — authors the `spec.md` this registry stores.
- `/sdd:mr` (sdd bundle) — publishes the spec to the registry this skill reads.
- `/sdd:doc-adr-query` — same query pattern, for architecture decisions.
- `/sdd:doc-catalog-query` — same query pattern, for service catalogs.
