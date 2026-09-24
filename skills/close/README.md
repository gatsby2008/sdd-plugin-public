# Close Feature

Wipes `.specwork/` clean. This is the canonical cleanup command for the SDD pipeline.

Two scenarios:

- **After your MR is merged** — clean up the artifacts from the finished feature so the workspace is ready for the next one.
- **Before starting a new feature** — use `/sdd:close` to clear stale `.specwork/` artifacts so `/sdd:start` can initialize a fresh pipeline cleanly.

Run from any branch. Does not require `glab` — but uses it (when available) to verify MR status.

**Branch and worktree safety:** beyond deleting the local `.specwork/` directory, `/sdd:close` only offers — on a feature branch, and only after you confirm — to delete that **local** branch and switch back to its parent. It never touches the **remote** branch (`git push origin --delete` stays your call) and never reverts or deletes code changes outside `.specwork/`. Decline the branch prompt (or run under `SDD_NON_INTERACTIVE`) and the branch is left exactly as-is.

---

## Usage

```bash
/sdd:close
```

---

## What It Does

1. Reads the current branch (best-effort context).
2. **If you're on a feature branch with a recognizable ticket and `glab` is installed**, checks the MR status:
   - Merged → proceeds normally
   - Open or closed-without-merge → warns and asks to confirm anyway
   - `glab` missing → warns and proceeds without the MR check
3. **Warns if a spec is still in `_spec/` and was never moved to `docs/specs/`** — running `/sdd:close` here loses the spec (`/sdd:mr` is what moves it).
4. Lists every file under `.specwork/` that will be deleted.
5. Asks for confirmation.
6. Wipes `.specwork/` entirely (files **and** folders). `/sdd:start` recreates the folders it needs on the next run.
7. **On a feature branch**, offers to delete the local branch and switch back to its parent (delete + switch / keep + switch / stay / quit). Skipped under `SDD_NON_INTERACTIVE`.

Nothing is committed — `.specwork/` is gitignored.
Tracked and untracked files outside `.specwork/` are preserved exactly as-is, so `git status` may still show source-tree changes after `/sdd:close`.

The spec at `docs/specs/<id>-spec.md` (moved there by `/sdd:mr`) is preserved as permanent documentation in the repo.

---

## Pipeline Position

```
/sdd:mr            ← moves spec to docs/specs/, creates or hands off the MR
/sdd:mr-address
/sdd:close         ← you are here, after MR is merged (or any time you need to reset)
```
