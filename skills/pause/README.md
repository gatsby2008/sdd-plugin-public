# Pause Feature

Stashes all work — including `.specwork/` artifacts — without switching branches.

Use when you need to context-switch away from the active pipeline branch mid-pipeline
without losing spec, plan, or progress files.

---

## Usage

```bash
/sdd:pause
```

---

## What It Does

1. Runs `git stash push --all` (captures gitignored `.specwork/` files)
2. Labels the stash `pause: <branch-name>` so `/sdd:restore` can identify it
3. Leaves branch switching to you

---

## Pipeline Position

```
/sdd:start
/sdd:implement → /sdd:commit   ← repeat per step
    ↓ need to switch context?
  /sdd:pause                 ←  you are here
  ... work elsewhere ...
  /sdd:restore                ←  come back here
    ↓
/sdd:test-design
/sdd:test-impl
/sdd:code-review
/sdd:mr
/sdd:mr-address
/sdd:close
```
