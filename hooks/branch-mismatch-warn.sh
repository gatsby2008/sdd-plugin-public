#!/usr/bin/env bash
# PreToolUse(Edit|Write) hook entrypoint: locate a Python 3 interpreter and hand
# the hook payload (JSON on stdin) to branch-mismatch-warn.py, which warns once
# per session when .specwork/ on disk belongs to a different branch than the one
# being edited. Mirrors check-python.sh's interpreter resolution (incl. the
# ~/.claude/bin/python3 shim) so it works on Windows + Git Bash.
#
# This fires on every file edit, so it pre-filters in shell before paying Python
# startup: no .specwork/_state in the working directory means there is no
# pipeline to be mismatched with, which is the common case in most repos. Hooks
# run with the project directory as cwd, and the Python side re-checks against
# the payload's own cwd, so a mis-guess here can only cost a warning, never
# produce a wrong one.
#
# Fails open (exit 0) when no interpreter is found — a warning must never wedge
# an edit.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -d ".specwork/_state" ] || exit 0

pick_python() {
  if command -v python3 >/dev/null 2>&1; then echo "python3"; return 0; fi
  if [ -x "${HOME}/.claude/bin/python3" ]; then echo "${HOME}/.claude/bin/python3"; return 0; fi
  if command -v python >/dev/null 2>&1 \
     && python -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then
    echo "python"; return 0
  fi
  if command -v py >/dev/null 2>&1 && py -3 -c "" 2>/dev/null; then echo "py -3"; return 0; fi
  return 1
}

PY="$(pick_python)" || exit 0
exec $PY "$DIR/branch-mismatch-warn.py"
