# Investigation Query

Ask questions across every investigation you've captured with `/sdd:doc-investigation`.

Once you've filed a few findings documents, this skill turns them into a searchable knowledge base — "have we hit this before?", "which bugs touched LeadService?", "what did we learn about the cache?" — reading directly from the central registry.

---

## Prerequisites

- At least one investigation captured via `/sdd:doc-investigation`.
- Read access to `~/.claude/investigation-registry/` (or your `$CLAUDE_DOC_HOME` override).

---

## Usage

```bash
/sdd:doc-investigation-query "what was the vehicle-lookup cache bug?"
/sdd:doc-investigation-query "which investigations touch LeadService?"
/sdd:doc-investigation-query "have we seen ReportToken reuse before?"
/sdd:doc-investigation-query "what future signals did we record for stale reads?"
```

---

## What It Does

Reads every captured investigation in scope and answers your question, citing the source file for each claim. When your question names a specific service (e.g. `lead-service`), it narrows to that subdir to save time; aggregate or recurrence questions ("ever", "have we seen", "across services") read the whole registry.

It understands the fixed structure of each document — Problem, Symptoms, Investigation, Findings, Root Cause, Fix, Related Classes, Future Signals — so it can answer recall, impact-scan, recurrence, and future-signal questions precisely.

---

## When to Use

- Before debugging something that feels familiar — check if it's already documented.
- When onboarding to a service and you want its accumulated war stories.
- To find the "check this first" heuristic you wrote for a class of symptoms.

---

## Output / Next Step

A cited answer in the session. If nothing matches, it tells you which service may be missing a capture so you can run `/sdd:doc-investigation`.

---

## Troubleshooting

**"No investigations found"**
The registry is empty. Capture one with `/sdd:doc-investigation` first.

**It read the whole registry when I wanted one service**
Name the service in kebab-case (e.g. `lead-service`) and avoid aggregate words like "ever" or "across services" in the same question.

**Team-shared findings**
Point `$CLAUDE_DOC_HOME` at the shared registry repo before querying.

---

## Related Skills

- `/sdd:doc-investigation` — captures the investigations this skill reads
- `/sdd:doc-adr-query` — query architecture decisions
- `/sdd:doc-spec-query` — query feature specs
- `/sdd:doc-catalog-query` — query service catalogs
