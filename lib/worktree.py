#!/usr/bin/env python3
"""Working-tree cleanliness checks for SDD skills.

Replaces ad-hoc ``git status --porcelain`` checks scattered across implement,
close, pause, resume and spec — including the subtle "clean except agent
files" variant. The porcelain parser is pure (testable without a git repo); thin
wrappers shell out to git.

CLI:
  python3 worktree.py is-clean [--exclude-agent-files]    # exit 0 clean, 1 dirty
  python3 worktree.py dirty-files [--exclude-agent-files] # one changed path per line
"""
import subprocess
import sys
from pathlib import PurePosixPath

# Per-tool instruction files that don't count as "real" changes for some gates.
AGENT_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")


def parse_porcelain(output, exclude_agent_files=False):
    """Changed file paths from ``git status --porcelain`` output.

    Handles rename entries (``orig -> new`` → keeps ``new``). When
    ``exclude_agent_files`` is set, drops top-level agent instruction files.
    """
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()  # porcelain v1: 2 status chars + space, then path
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        files.append(path)
    if exclude_agent_files:
        files = [f for f in files if PurePosixPath(f).name not in AGENT_FILES]
    return files


def _git_porcelain():
    try:
        return subprocess.check_output(["git", "status", "--porcelain"]).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def dirty_files(exclude_agent_files=False):
    return parse_porcelain(_git_porcelain(), exclude_agent_files)


def is_clean(exclude_agent_files=False):
    return not dirty_files(exclude_agent_files)


def _main(argv):
    exclude = "--exclude-agent-files" in argv
    cmd = argv[0] if argv else ""
    if cmd == "is-clean":
        sys.exit(0 if is_clean(exclude) else 1)
    if cmd == "dirty-files":
        for f in dirty_files(exclude):
            print(f)
        sys.exit(0)
    print("Usage: worktree.py <is-clean|dirty-files> [--exclude-agent-files]")
    sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
