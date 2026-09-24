# MR Description

Generates a concise MR title/description from branch commits and spec (if present),
then pushes and opens or updates the MR.

Works with or without `.specwork` artifacts.

---

## Usage

```bash
/sdd:mr
/sdd:mr PROJ-15535
```

---

## Preconditions

- active pipeline branch, or any current branch when running without `.specwork`
- at least one commit on branch
- optional: `glab` for automatic create/update

Manual mode is always available when `glab` is missing.

---

## Flow

1. detect branch and ticket/slug
2. target branch: `development` (default); override with `--target <branch>`
3. read spec if present (`.specwork/_spec/<id>-spec.md`)
4. publish spec in-repo to `docs/specs/<id>-spec.md` and commit it — skipped silently when no `.specwork` spec exists
5. read commit history vs target branch
6. run behind check (`fetch` + `rev-list`)
7. offer `rebase / skip / cancel` when behind
8. **run test validation** — via `bash commands/check.sh` (auto-detects: Gradle, Maven, npm/pnpm/yarn, pytest, Cargo, Go)
   - if tests fail → stop, do not push
   - if tests pass → continue
9. generate MR title + short description
10. push branch
11. create/update via `glab` or print manual GitLab URL + copy/paste body
12. publish spec to the central registry (`$CLAUDE_DOC_HOME/spec-registry/<service>/<id>-spec.md`) when a `.specwork` spec exists — skipped silently otherwise

---

## Output

```text
Title: [PROJ-1234] feat: <short summary>

Summary:
- what changed
- why
- key risks/notes

Testing:
- <short list>
```

Keep output short by default.

---

## Rules

- prefer spec + commits as source of truth
- do not block if `.specwork` artifacts are missing
- **validate tests before push** — if tests fail, stop and show error
- never force-push automatically
- stop on push/rebase/test failures and show the error
- optional: `--skip-validation` flag to bypass test check (for emergencies only)

---

## Related Skills

- `/sdd:commit` — finalize commits before MR
- `/sdd:mr-address` — process review comments
- `/sdd:close` — clean `.specwork/` after merge
