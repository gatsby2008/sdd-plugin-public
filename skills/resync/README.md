# Resync

Sync SDD pipeline artifacts under `.specwork/` with the current branch when the branch was renamed. Renames the state, spec, source, plan, cache, path, and context files; updates `state.json` to reflect the new branch (and any extractable ticket).

## Usage

```bash
/sdd:resync                              # sync-only — use after `git branch -m`
/sdd:resync --rename-branch feature/IR-70-foo  # atomic — rename branch then sync
```

## Examples

**Free-text feature gets assigned a ticket.** Branch was `feature/consent-personuuid`, now there's an IR-70 ticket:

```bash
/sdd:resync --rename-branch feature/IR-70-consent-personuuid
```

Result:

```
Branch:  feature/consent-personuuid   →  feature/IR-70-consent-personuuid
Slug:    consent-personuuid           →  ir-70-consent-personuuid
Ticket:  null                         →  IR-70
Type:    freetext                     →  jira
Files renamed: 6
```

**Manual rename already happened.** Branch was renamed via `git branch -m` and now the pipeline doesn't recognize it:

```bash
/sdd:resync
```

The skill detects the mismatch between the current branch and `state.json::branch`, and updates the pipeline to match.

**Dotted ticket convention** (`IR-70.1`):

```bash
/sdd:resync --rename-branch feature/IR-70.1-payment-flow
```

The slug becomes `ir-70-1-payment-flow` (dots collapsed to hyphens for filesystem safety), `ticket` is stored as `"IR-70.1"` (preserved as-is), and `input_type` stays `"freetext"` because dotted keys are not queryable via the Jira API.

## What it does not do

- **Does not touch the remote.** If the old branch was pushed to origin, you need to `git push -u origin HEAD` and `git push origin --delete <old-branch>` yourself.
- **Does not modify `source_title`.** That field captures the original `/sdd:start` input. If the rename surfaced a ticket, edit `source_title` manually or rerun `/sdd:start` to refetch from Jira.
- **Does not merge state files.** A collision against a different existing slug aborts with a manual-cleanup message — it never overwrites another pipeline's state.

## Requirements

- A SDD pipeline must be initialized in `.specwork/` (at least one `*-state.json` under `.specwork/_state/`). Otherwise the skill exits cleanly with "nothing to resync".

## Related Skills

- `/sdd:start` — initializes the pipeline this skill resyncs.
- `/sdd:whatnext` — blocks when the current branch does not match `state.json::branch`; running `/sdd:resync` first unblocks it.
- `/sdd:close` — wipes `.specwork/` after a feature is merged.
