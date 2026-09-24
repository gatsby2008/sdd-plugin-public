# Ingest — compile raw → wiki

Compiles the append-only `raw/` layer of a two-layer knowledge vault into the
interconnected `wiki/` layer: extracts **entities** and **concepts**, writes typed
markdown pages with `[[backlinks]]`, keeps the indexes current, and appends to the log.

It's the **producer half** of the Karpathy two-layer model (Andrej Karpathy's "LLM
Knowledge Bases"):

```
raw/  (source of truth)          wiki/  (compiled, interconnected)
  service-catalog/  ── ingest ──►  entities/   concepts/   sources/
  adr-registry/                    with [[backlinks]] + indexes + log.md
  investigation-registry/
  spec-registry/  + hand-added sources
```

The SDD `doc-*` commands write `raw/`. **`doc-ingest` is what turns that raw material into
the wiki graph** that `/sdd:ask` navigates — the step that was previously done by hand.

## When it runs

Only where `$CLAUDE_DOC_HOME` is a **two-layer vault** — i.e. there's a `wiki/` directory
next to `raw/`. On a plain registry (the default `~/.claude`, no wiki) it stops cleanly:
there's nothing to compile into.

## Usage

```bash
/sdd:doc-ingest raw/service-catalog/leads-service.md   # compile one source
/sdd:doc-ingest session                                # distill the current session into the wiki
/sdd:doc-ingest                                        # auto: compile whatever raw/ is un-ingested
```

## What it does

1. **Reads the vault schema** (`<vault>/CLAUDE.md`) and follows it — the schema owns the
   page conventions (frontmatter, `## Source`, controlled `subtype` vocab) and can
   co-evolve without changing this skill.
2. **Extracts** the entities and concepts a source introduces; **creates or updates in
   place** their wiki pages (never duplicates), in your own words, with `[[wikilinks]]`
   and a `## Source` link back to `raw/`.
3. **Updates** the folder-note indexes + `wiki.md`, and **appends** a `wiki/log.md` entry.
4. **Verifies 0 broken links** and reports pages created vs. updated.

## Why it matters

`raw/` is the source of truth but it's flat and per-registry. The `wiki/` layer is the
**explainable-RAG index**: explicit `[[backlinks]]` you can audit, instead of opaque
vector similarity. Keeping it compiled is what lets `/sdd:ask` answer cross-cutting
questions ("who consumes X, why we designed it that way, and which spec touched it") by
following links across catalogs, ADRs, specs and investigations at once.

## Related Skills

- `/sdd:ask` — the consumer: navigates this wiki, grounded in `raw/`, and warns when the
  wiki is behind (i.e. when `doc-ingest` should be run).
- `/sdd:doc-catalog`, `/sdd:doc-adr`, `/sdd:doc-spec`, `/sdd:doc-investigation` — populate the
  `raw/` registries this skill compiles.
