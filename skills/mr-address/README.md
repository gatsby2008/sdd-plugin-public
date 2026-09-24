# Address MR Review

Addresses unresolved MR review comments one thread at a time.
Tracks progress in `.specwork/_review/<id>-mr-address.md`.

`glab` is optional:
- with `glab`: fetch/reply/resolve automatically
- without `glab`: paste comments manually and continue

---

## Usage

```bash
/sdd:mr-address
/sdd:mr-address PROJ-15535
```

---

## Flow

1. Detect MR context and `glab` availability
2. Load unresolved threads (or pasted comments in manual mode)
3. Skip already handled entries from progress file
4. Process each thread with one action
5. Offer commit/push if files changed

---

## Per-Thread Actions

- `fix` — apply code fix, confirm, resolve
- `reply` — send or print reply text, resolve
- `defer` — record as pending
- `skip` — ignore and continue
- `done` — stop session

Keep context minimal: only current thread + relevant lines.

---

## Progress File

Saved at:

```text
.specwork/_review/<id>-mr-address.md
```

Used to skip already handled threads on later runs.

---

## End of Session

Prints a short summary (`fixed`, `replied`, `deferred`, `skipped`).
If files changed, offers one commit and optional push.

---

## Troubleshooting

**No open MR found**
Run `/sdd:mr` first.

**`glab` unavailable**
Continue in manual mode.

**API resolve failed**
Mark the thread resolved manually in GitLab UI.

---

## Related Skills

- `/sdd:mr` — opens/updates the MR
- `/sdd:commit` — manual commit flow
- `/sdd:code-review` — pre-MR internal review
