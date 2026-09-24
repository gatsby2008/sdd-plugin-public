# Undo Implementation

Discard **uncommitted** code changes — reversibly — before they are committed.
Works inside a pipeline (preserves `.specwork/` so you can fix the spec and
re-implement) **and standalone for vibe coding** (no `.specwork/` required; just
cleans your working tree). Reversible by default.

---

## Usage

```bash
/sdd:undo            # reversible: stash the implementation
/sdd:undo --restore  # recover the last undone implementation (redo)
/sdd:undo --hard     # irreversible: revert tracked edits + delete new files
```

---

## What It Does

1. **Previews** the tracked edits and new files that will be discarded (`.specwork/`
   never appears — it is gitignored).
2. **Confirms** with you (reversible undo and `--hard`).
3. Runs the matching action:
   - default → `git stash push --include-untracked -m "undo: <slug>"` (recoverable)
   - `--restore` → `git stash pop` the newest `undo` stash
   - `--hard` → `git restore .` + `git clean -fd` (never `-x`, so `.specwork/` survives)
4. Points you back to `/sdd:spec` → `/sdd:plan` → `/sdd:implement`.

`.specwork/` (spec, plan, cache, state) is **always preserved**, so the pipeline
stays alive — only the failed implementation is discarded.

---

## Not `/sdd:pause`, not `/sdd:close`

| Command | Code changes | `.specwork/` |
|---------|--------------|--------------|
| **`/sdd:undo`** | discarded (reversible) | **kept** |
| `/sdd:pause` | stashed to switch branches | stashed too |
| `/sdd:close` | left untouched | wiped |

`/sdd:undo` only handles **uncommitted** work. If the implementation is already
committed, that is a `git reset` operation — the skill explains the options
instead of rewriting history.

---

## Pipeline Position

```
/sdd:start → /sdd:spec → /sdd:plan → /sdd:implement
                                    ↓ implementation is wrong?
                                 /sdd:undo          ← you are here
                                    ↓ (.specwork/ intact)
                              /sdd:spec → /sdd:plan → /sdd:implement
                                    ↓
                                 /sdd:commit
```
