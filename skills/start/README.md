# Start

Initialize the SDD pipeline on your current branch or create a new working branch.

Fetches Jira ticket (optional), initializes `.specwork/` folders, and writes the state and source
that all downstream skills depend on. It does **not** write the spec — drafting `spec.md` is `/sdd:spec`'s
job; run `/sdd:spec` next. Flexible branch handling: from any branch, `/sdd:start` can create
a new working branch from the current branch HEAD, or initialize on the current branch when that is
the better choice. This supports dependent feature branches such as creating `feature/IR-45` while
currently on `feature/IR-40`, so the new branch inherits the parent work.

---

## Usage

```bash
/sdd:start PROJ-1234              # from Jira ticket
/sdd:start "fix duplicate leads"   # free-text description
```

---

## What It Does

1. **Detects current branch**: uses the current branch as the starting context
2. **Pre-flight checks**: 
   - If creating from `development`/`main`: require clean working tree (agent-memory files like `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` are exempt — they ride onto the new branch)
   - If starting from another branch: use that branch as the base for the new branch or current-branch flow
    - Empty `.specwork/` (auto-cleans merged features)
 3. **Classifies input**: Jira ticket or free-text
 4. **Fetches Jira** (optional, via Jira REST with `curl`; falls back to freetext)
 5. **Branch handling**:
    - Offers a suggested branch name based on the ticket or free-text input
    - Can create that branch from the current branch HEAD so it inherits parent work
    - Can keep the current branch and append pipeline state there
 6. **Sets up `.specwork/`**: `_spec/`, `_state/`, `_progress/`, `.gitignore`, pipeline permissions
 7. **Writes state file**: `.specwork/_state/<slug>-state.json`
 8. **Captures the source**: `.specwork/_spec/<slug>-source.md`
 9. **Gitignores `.specwork/`**: appends `.specwork/` to `.gitignore` (creates it if absent); warns if `.specwork/` is already tracked
 10. **Hands off to `/sdd:spec`**: the spec is **not** written here. `/sdd:spec` drafts `.specwork/_spec/<slug>-spec.md` from the captured source (sections: Summary, Scope, Behavior, Implementation Context, **Expected Change Scope**, **Safe Constraints**, Open Questions), runs triage, and owns the Open Questions summary.

### Spec sections consumed by `/sdd:handoff`

The spec (written by `/sdd:spec`) includes two sections that `/sdd:handoff` extracts **verbatim** when building the execution capsule:

- **`## Expected Change Scope`** — expected files touched (range), expected layers, areas to avoid touching
- **`## Safe Constraints`** — explicit *Safe* and *Unsafe* operation lists

Both must be filled in concrete plain language. If a field is genuinely unknown, write `[UNKNOWN]` rather than guessing — `/sdd:handoff` will copy that through to the executor model unchanged.

All downstream skills read this state file — no re-fetching or re-classifying.

---

## State File

`/sdd:start` writes `.specwork/_state/<slug>-state.json`:

```json
{
  "id": "proj-1234",
  "ticket": "PROJ-1234",
  "input_type": "jira",
  "branch": "feature/PROJ-1234",
  "base_branch": "development",
  "source_title": "User Consent Email Integration",
  "source_body_file": ".specwork/_spec/proj-1234-source.md",
  "spec_file": ".specwork/_spec/proj-1234-spec.md",
  "context_file": ".specwork/_progress/proj-1234-context.md",
  "rules_file": ".specwork/_state/proj-1234-rules.json",
  "implementation_cache_file": ".specwork/_state/proj-1234-implementation-cache.json"
}
```

All downstream skills read this state file — no re-fetching or re-classifying.

---

## Implementation Cache

`/sdd:start` initializes an empty `.specwork/_state/<slug>-implementation-cache.json`. `/sdd:spec` and `/sdd:plan` later prefill it with confirmed facts from the spec so `/sdd:implement` avoids rediscovery:

```json
{
  "schema_version": 1,
  "id": "proj-1234",
  "repositories": [],
  "patterns": [],
  "related_tests": [],
  "similar_classes": [],
  "notes": []
}
```

**How it works:**
- `/sdd:spec` / `/sdd:plan` may add confirmed repositories, classes, or tests from the spec
- `/sdd:implement` reads the cache to avoid repo scans, then appends discovered facts
- Reduces token consumption in later steps by ~15-40% (no redundant discovery)

The cache is **append-only** — facts accumulate across the feature lifecycle.

---

## Jira Setup Without MCP

`/sdd:start` can fetch a Jira issue directly with `curl` through `${CLAUDE_PLUGIN_ROOT}/lib/jira.sh`.

On macOS/zsh, put this in `~/.zshenv`:

```zsh
export JIRA_BASE_URL="https://your-company.atlassian.net"
export JIRA_USER="your.email@company.com"
export JIRA_TOKEN="your-atlassian-api-token"
```

Security note:
- Do not put real Jira credentials in project files.
- Keep them in user-level shell config (for example `~/.zshenv`) outside git.
- Commit only placeholder values in documentation.

For Jira Server/Data Center with PAT auth:

```zsh
export JIRA_BASE_URL="https://jira.your-company.internal"
export JIRA_AUTH_MODE="bearer"
export JIRA_TOKEN="your-personal-access-token"
```

If those variables are present and the input looks like a ticket key, `/sdd:start` saves a Jira dump to `.specwork/_spec/<slug>-source.md` (which `/sdd:spec` later drafts the spec from). If not, it still writes the state file, captures source manually, and continues in free-text mode.

---

## Requirements

**If on `development`, `develop`, `main`, or `master`:**
- Clean working tree (required)
- `.specwork/` empty (or auto-cleaned from merged features)

**If on any other branch:**
- `.specwork/` empty (or auto-cleaned from merged features)
- Dirty tree allowed (assumes existing feature work)

**General:**
- Jira REST credentials optional (falls back to freetext if unavailable)

---

## Next Step

```bash
/sdd:spec
```

---

## Pipeline Flow

```
/sdd:start → /sdd:spec → /sdd:plan (optional) → /sdd:implement → /sdd:commit
           → /sdd:test-design → /sdd:test-impl   (optional)
           → /sdd:code-review                  (optional)
           → /sdd:mr → /sdd:mr-address → /sdd:close
```
