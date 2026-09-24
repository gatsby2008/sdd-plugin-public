#!/usr/bin/env python3
"""PostToolUse(Bash) hook: remind to re-key the pipeline after a branch change.

The footgun: ``.specwork/`` is **branch-keyed** (state.json records the branch,
artifacts are named ``<slug>-*``) but it is **gitignored**, so it does NOT move
when you change branches. After ``git branch -m`` (rename) or ``git checkout``/
``git switch`` to another branch, the on-disk pipeline still belongs to the old
branch — silently out of sync.

This is *awareness*, not enforcement: it never blocks (the branch change already
happened), it just surfaces a ``systemMessage`` when it detects the mismatch.

Accuracy over pattern-matching: it only fires when **no** ``state.json`` records
the *current* branch — i.e. the pipeline on disk really is keyed to a different
branch. So ``git checkout -- file`` (no branch change) and switching *back* to the
pipeline's own branch stay silent. The command verb only tailors the wording
(rename → ``/sdd:resync``; switch → ``/sdd:pause`` + ``/sdd:restore``).

Scope: only inside an active pipeline (``.specwork/_state`` present). Fails silent
(exit 0, no message) on any internal error — a reminder must never disrupt work.
"""
import glob
import json
import os
import shlex
import subprocess
import sys

# git global options that consume the following token as their argument.
_GIT_OPT_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
# flags that make `git branch` a rename rather than a list/delete/etc.
_BRANCH_MOVE_FLAGS = {"-m", "-M", "--move"}


def branch_change_flavor(cmd):
    """Classify a command as a branch change: "rename", "switch", or None.

    "switch"  → ``git checkout <branch>`` / ``git switch <branch>`` (incl. -b/-c).
    "rename"  → ``git branch -m|-M|--move ...``.
    Anything else (``git branch -d``, ``git status``, non-git) → None.
    Only the *first* git segment is inspected; the accurate sync check below is
    what actually decides whether to warn.
    """
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    if "git" not in toks:
        return None
    j = toks.index("git") + 1
    while j < len(toks):
        t = toks[j]
        if t in _GIT_OPT_WITH_ARG:
            j += 2
            continue
        if t.startswith("-"):
            j += 1
            continue
        # t is the git subcommand.
        if t in ("checkout", "switch"):
            return "switch"
        if t == "branch" and any(f in _BRANCH_MOVE_FLAGS for f in toks[j + 1 :]):
            return "rename"
        return None
    return None


def current_branch():
    """Current branch name, or "HEAD" when detached, or "" on error."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def recorded_branches(state_dir=".specwork/_state"):
    """Every branch recorded across ``*-state.json`` files (de-duplicated)."""
    branches = []
    for path in glob.glob(os.path.join(state_dir, "*-state.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                b = json.load(fh).get("branch")
            if b:
                branches.append(b)
        except Exception:
            continue
    return branches


def build_message(flavor, recorded, current):
    """Compose the reminder, leading with the fix most likely for ``flavor``."""
    where = recorded[0] if recorded else "another branch"
    head = "a detached HEAD" if current == "HEAD" else "'{}'".format(current)
    resync = (
        "  • If you RENAMED the branch (git branch -m): run /sdd:resync to "
        "re-key the pipeline to {}.".format(head)
    )
    switch = (
        "  • If you SWITCHED to a different feature: the pipeline for '{}' is now "
        "detached here — run /sdd:restore to restore its paused state, or "
        "/sdd:pause before leaving next time.".format(where)
    )
    order = [resync, switch] if flavor == "rename" else [switch, resync]
    return "\n".join(
        [
            "⚠️ SDD: .specwork/ is keyed to '{}', but you are now on {}.".format(
                where, head
            ),
            ".specwork/ is gitignored, so it did not move with the branch change.",
            *order,
        ]
    )


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    flavor = branch_change_flavor(cmd)
    if flavor is None:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    try:
        os.chdir(cwd)
    except Exception:
        pass

    # Scope: only inside an active SDD pipeline.
    if not os.path.isdir(".specwork/_state"):
        return 0

    try:
        recorded = recorded_branches()
        current = current_branch()
        if not current or not recorded:
            return 0
        # In sync: some pipeline on disk already owns the current branch.
        if current in recorded:
            return 0
        msg = build_message(flavor, recorded, current)
    except Exception:
        return 0  # never disrupt — a reminder failing is not worth an error

    # systemMessage surfaces the note without the "blocking error" framing of
    # exit 2; the branch change already happened, so there is nothing to block.
    sys.stdout.write(json.dumps({"systemMessage": msg}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
