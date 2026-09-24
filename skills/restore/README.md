# Restore Feature

Lists paused pipeline branches and restores the one you select.

Filters stashes to show only those created by `/sdd:pause` (i.e. branches that
were following the SDD pipeline). Non-pipeline stashes are hidden.

---

## Usage

```bash
/sdd:restore
```

---

## What It Shows

```
Paused pipeline branches:

  [0]  feature/PROJ-15535   step 4/9 done — next: "Add ConsentController"
  [1]  feature/PROJ-16843   step 1/5 done — next: "Update Lead entity"

  (2 other stashes exist but have no pipeline context)

Resume which branch? (0 / 1 / cancel)
```

On selection: verifies the current working tree is clean, switches to the recorded branch, and pops the correct stash.

If a branch was paused more than once, only its most recent stash is shown
(`/sdd:restore` warns about the older ones and drops them after a successful resume),
so the menu lists each branch exactly once.

---

## Pipeline Position

```
/sdd:start
/sdd:implement → /sdd:commit
    ↓ need to switch context?
  /sdd:pause
  ... work elsewhere ...
  /sdd:restore                ←  you are here
    ↓
/sdd:implement (continues from where you left off)
```
