#!/usr/bin/env python3
"""Commit / MR title formatting for commit and mr.

The mechanical parts — extracting the ticket from the branch and assembling the
`[TICKET] <type>: <summary>` string — live here (ticket extraction reuses
slug.py). The `<type>` and `<summary>` remain the model's judgment; this module
only formats what it is given.

CLI:
  python3 titles.py ticket <branch>
  python3 titles.py commit-subject <branch> <type> <summary...>
  python3 titles.py mr-title <branch> <type> <summary...>
"""
import sys

import slug


def ticket_from_branch(branch):
    """Canonical ticket key from a branch (e.g. ``PROJ-123``), or ``""``."""
    return slug.ticket_from_branch(branch)[0]


def commit_subject(branch, change_type, summary):
    """``[TICKET] <type>: <summary>`` — ``[NO-TICKET]`` when the branch has none."""
    ticket = ticket_from_branch(branch) or "NO-TICKET"
    return f"[{ticket}] {change_type}: {summary}"


def mr_title(branch, change_type, summary):
    """``[TICKET] <type>: <summary>``, or ``<type>: <summary>`` when no ticket."""
    ticket = ticket_from_branch(branch)
    prefix = f"[{ticket}] " if ticket else ""
    return f"{prefix}{change_type}: {summary}"


def _main(argv):
    if not argv:
        print("Usage: titles.py <ticket|commit-subject|mr-title> <branch> [type] [summary...]")
        sys.exit(2)
    cmd, rest = argv[0], argv[1:]
    if cmd == "ticket":
        print(ticket_from_branch(rest[0]))
        return
    branch, change_type, summary = rest[0], rest[1], " ".join(rest[2:])
    if cmd == "commit-subject":
        print(commit_subject(branch, change_type, summary))
    elif cmd == "mr-title":
        print(mr_title(branch, change_type, summary))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
