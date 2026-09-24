#!/usr/bin/env python3
"""Branch classification and base-branch resolution for SDD skills.

Centralizes the "what kind of branch is this / must the tree be clean / what is
the parent branch" decisions duplicated across start, close, resync and
handoff.

CLI:
  python3 branches.py classify <branch>
  python3 branches.py requires-clean-tree <branch>   # exit 0 if yes, 1 if no
  python3 branches.py base <branch> [state_base] [default]
"""
import re
import sys

_PREFIX_RE = re.compile(r"^(feature|hotfix|release|bugfix)/")
_SHARED_BASE = {"main", "master", "develop", "development"}


def classify_branch(branch):
    """Return ``feature|hotfix|release|bugfix|main|develop|other``."""
    m = _PREFIX_RE.match(branch)
    if m:
        return m.group(1)
    if branch in ("main", "master"):
        return "main"
    if branch in ("develop", "development"):
        return "develop"
    return "other"


def is_feature_branch(branch):
    """True for the prefixed working-branch kinds (feature/hotfix/release/bugfix)."""
    return classify_branch(branch) in ("feature", "hotfix", "release", "bugfix")


def requires_clean_tree(branch):
    """True for shared base branches where /sdd:start must branch off a clean tree."""
    return branch in _SHARED_BASE


def detect_base_branch(branch, state_base="", default="development"):
    """Resolve the parent/base branch: the value recorded in state wins, else default."""
    return state_base or default


def _main(argv):
    if len(argv) < 2:
        print("Usage: branches.py <classify|requires-clean-tree|base> <branch> [args]")
        sys.exit(2)
    cmd, branch = argv[0], argv[1]
    if cmd == "classify":
        print(classify_branch(branch))
    elif cmd == "requires-clean-tree":
        sys.exit(0 if requires_clean_tree(branch) else 1)
    elif cmd == "base":
        state_base = argv[2] if len(argv) >= 3 else ""
        default = argv[3] if len(argv) >= 4 else "development"
        print(detect_base_branch(branch, state_base, default))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
