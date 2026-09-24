#!/usr/bin/env python3
"""Undo an in-progress implementation without touching `.specwork/`.

Backs `/sdd:undo`. The whole point is to discard the code changes accumulated by
`/sdd:implement` (pre-commit) while keeping the pipeline state — spec, plan, cache,
state.json — intact so you can re-spec and re-implement.

That separation is free from git's own rules: `.specwork/` is gitignored, so it
never appears in `git status --porcelain`, is never stashed by
`git stash --include-untracked` (stash skips ignored files), and is never removed
by `git clean -fd` (only `-x` would touch ignored files). This module relies on
exactly that invariant and never passes `-x`.

Two modes:
  - reversible (default): `git stash push --include-untracked` with an
    ``undo: <slug>`` message; recover with `restore` (`git stash pop`).
  - hard: `git restore .` + `git clean -fd` — irreversible.

Pure parsers are testable without a git repo; thin wrappers shell out.

CLI:
  python3 revert.py preview               # affected paths (porcelain; .specwork excluded)
  python3 revert.py undo [--slug <slug>]  # reversible: stash code changes
  python3 revert.py restore               # pop the newest undo stash (redo)
  python3 revert.py list                  # undo stashes: "<ref>\t<slug>", newest first
  python3 revert.py hard                   # irreversible: restore + clean -fd
"""
import subprocess
import sys

# Same dir at runtime (skills call `python3 .../lib/revert.py`) and under tests
# (tests insert lib/ on sys.path), so a plain import resolves either way.
import worktree

UNDO_PREFIX = "undo: "


# --- pure parsers -----------------------------------------------------------

def parse_undo_stashes(stash_list_output):
    """``[(ref, slug), ...]`` for undo stashes, in input order (newest-first).

    Input is ``git stash list --format='%gd %s'``. Non-undo stashes (manual
    stashes, ``/sdd:pause`` entries) are ignored so `restore` never pops unrelated
    work.

    ``git stash push -m "undo: <slug>"`` stores the subject as
    ``On <branch>: undo: <slug>`` — git prepends ``On <branch>: ``. So the
    marker is located anywhere in the message, not just at position 0, and the
    slug is whatever follows it.
    """
    out = []
    for line in stash_list_output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        ref, _, msg = line.partition(" ")
        idx = msg.find(UNDO_PREFIX)
        if idx != -1:
            out.append((ref, msg[idx + len(UNDO_PREFIX):].strip()))
    return out


def latest_undo_stash(stash_list_output):
    """Newest undo stash ref, or ``None`` when there is none."""
    stashes = parse_undo_stashes(stash_list_output)
    return stashes[0][0] if stashes else None


# --- thin git wrappers ------------------------------------------------------

def affected_paths():
    """Paths `/sdd:undo` would discard: everything in porcelain (ignored excluded)."""
    return worktree.dirty_files()


def _git_stash_list():
    try:
        return subprocess.check_output(
            ["git", "stash", "list", "--format=%gd %s"]
        ).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def do_undo(slug):
    """Reversible undo: stash tracked + untracked changes, keep `.specwork/`."""
    if not affected_paths():
        return 1, "Nothing to undo — the working tree is already clean."
    msg = UNDO_PREFIX + (slug or "wip")
    try:
        subprocess.check_call(
            ["git", "stash", "push", "--include-untracked", "-m", msg]
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return 1, f"git stash failed: {e}"
    return 0, f"Stashed implementation as '{msg}'. Recover with: /sdd:undo --restore"


def do_restore():
    """Pop the newest undo stash (the redo half of the undo)."""
    ref = latest_undo_stash(_git_stash_list())
    if ref is None:
        return 1, "No undo stash to restore."
    try:
        subprocess.check_call(["git", "stash", "pop", ref])
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return 1, f"git stash pop failed: {e}"
    return 0, f"Restored {ref}."


def do_hard():
    """Irreversible undo: revert tracked edits and delete untracked files.

    Never passes ``-x`` to ``git clean`` so ignored paths — `.specwork/` — survive.
    """
    if not affected_paths():
        return 1, "Nothing to undo — the working tree is already clean."
    try:
        subprocess.check_call(["git", "restore", "."])
        subprocess.check_call(["git", "clean", "-fd"])
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return 1, f"git revert failed: {e}"
    return 0, "Reverted working tree (.specwork/ preserved)."


def _main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "preview":
        paths = affected_paths()
        if not paths:
            print("(clean — nothing to undo)")
            sys.exit(1)
        for p in paths:
            print(p)
        sys.exit(0)
    if cmd == "list":
        for ref, slug in parse_undo_stashes(_git_stash_list()):
            print(f"{ref}\t{slug}")
        sys.exit(0)
    if cmd == "undo":
        slug = None
        if "--slug" in argv:
            i = argv.index("--slug")
            if i + 1 < len(argv):
                slug = argv[i + 1]
        code, msg = do_undo(slug)
        print(msg)
        sys.exit(code)
    if cmd == "restore":
        code, msg = do_restore()
        print(msg)
        sys.exit(code)
    if cmd == "hard":
        code, msg = do_hard()
        print(msg)
        sys.exit(code)
    print("Usage: revert.py <preview|undo [--slug <slug>]|restore|list|hard>")
    sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
