#!/usr/bin/env python3
"""Pipeline stash filtering for pause / resume.

/sdd:pause stores work with a ``pause: <branch>`` stash message. This module
parses ``git stash list``, keeps only pipeline stashes, extracts the branch, and
deduplicates (newest per branch kept; older ones are stale duplicates to drop).
Parsers are pure (testable without git); thin wrappers shell out.

CLI:
  python3 stash.py list    # kept pipeline stashes: "<ref>\t<branch>", newest per branch
  python3 stash.py stale   # stale duplicate refs (older repeats), one per line
"""
import subprocess
import sys

PAUSE_PREFIX = "pause: "


def parse_stash_list(output):
    """Parse ``git stash list --format='%gd %s'`` into ``[(ref, message), ...]``."""
    entries = []
    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        ref, _, msg = line.partition(" ")
        entries.append((ref, msg))
    return entries


def pipeline_stashes(output):
    """``[(ref, branch), ...]`` for pause stashes, in input order (newest-first)."""
    out = []
    for ref, msg in parse_stash_list(output):
        if msg.startswith(PAUSE_PREFIX):
            out.append((ref, msg[len(PAUSE_PREFIX):].strip()))
    return out


def deduplicate(pipeline_list):
    """Return ``(kept, stale)``: first (newest) per branch kept, the rest are stale."""
    seen = set()
    kept, stale = [], []
    for ref, branch in pipeline_list:
        if branch in seen:
            stale.append((ref, branch))
        else:
            seen.add(branch)
            kept.append((ref, branch))
    return kept, stale


def _git_stash_list():
    try:
        return subprocess.check_output(["git", "stash", "list", "--format=%gd %s"]).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _main(argv):
    cmd = argv[0] if argv else ""
    kept, stale = deduplicate(pipeline_stashes(_git_stash_list()))
    if cmd == "list":
        for ref, branch in kept:
            print(f"{ref}\t{branch}")
    elif cmd == "stale":
        for ref, _ in stale:
            print(ref)
    else:
        print("Usage: stash.py <list|stale>")
        sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
