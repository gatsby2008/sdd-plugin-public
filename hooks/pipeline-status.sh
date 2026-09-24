#!/usr/bin/env bash
# SessionStart hook entrypoint: locate a Python 3 interpreter and hand the hook
# payload (JSON on stdin) to pipeline-status.py, which prints a compact SDD
# pipeline status when one is active. Runs once per session (no pre-filter
# needed). Mirrors check-python.sh's interpreter resolution (incl. the
# ~/.claude/bin/python3 shim) so it works on Windows + Git Bash. Wired to run
# AFTER check-python.sh so the shim already exists. Fails open (exit 0) when no
# interpreter is found — a status line must never wedge a session.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
exec $PY "$DIR/pipeline-status.py"
