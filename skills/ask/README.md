# Ask — unified knowledge query

One query for the whole docs-registry. `/sdd:ask` answers any cross-service knowledge
question — services, decisions, specs, investigations — instead of making you pick the
right `doc-*-query`.

## The design in one line

**Navigate the `wiki/` index, land on `raw/` (the source of truth).**

- `raw/` (`$CLAUDE_DOC_HOME`) is written directly by the `doc-*` commands → always current
  → every answer is grounded there.
- `wiki/` (when the vault has a compiled layer) is an explainable-RAG index of
  `[[backlinks]]` → makes cross-cutting questions cheap. It can lag; `ask` warns and falls
  back to `raw/` when it does.

So `ask` is **reliable even if `/sdd:doc-ingest` hasn't run** — a stale or absent wiki
degrades it gracefully to "the four typed queries, merged" rather than a wrong answer.

## Usage

```bash
/sdd:ask who consumes the LeadCreated event and why did we design it that way?
/sdd:ask what breaks if leads-service goes down?
/sdd:ask have we seen ReportToken reuse before?
/sdd:ask which services depend on package-orchestrator?  type:catalog
```

Add `type:catalog` / `type:adr` / `type:spec` / `type:investigation` to scope to one
registry (reproducing a single-registry query); omit it to search across all four.

## What it does

1. Optional `type:` scope.
2. If a `wiki/` layer exists → reads `wiki.md` + folder-notes, follows `[[backlinks]]` to
   find what's relevant and which `raw/` sources it cites.
3. Reads the actual `raw/` files (the facts); falls back to grepping `raw/` directly when
   the wiki has no page or isn't there.
4. **Staleness check** — if `raw/` has sources added since the last ingest that bear on
   the question, it warns (and still answers from `raw/`).
5. Answers, citing `raw/` files (and the wiki pages it navigated through).

## Supersedes

`/sdd:ask` subsumes `/sdd:doc-catalog-query`, `/sdd:doc-adr-query`, `/sdd:doc-spec-query`, and
`/sdd:doc-investigation-query` — those read one registry each; `ask` reads across all of
them and can still scope with `type:`.

## Related Skills

- `/sdd:doc-ingest` — builds/refreshes the `wiki/` layer `ask` navigates.
- The `doc-*` create commands — populate the `raw/` registries `ask` grounds answers in.
