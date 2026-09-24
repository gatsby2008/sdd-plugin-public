#!/usr/bin/env bash
# PreToolUse(Bash) hook entrypoint: locate a Python 3 interpreter and hand the
# hook payload (JSON on stdin) to push-gate.py, which enforces the SDD quality
# gate on `git push` calls (HEAD must have passed commands/check.sh). Mirrors
# check-python.sh's interpreter resolution (incl. the ~/.claude/bin/python3 shim)
# so it works on Windows + Git Bash. Fails open (exit 0) when no interpreter is
# found — the SessionStart hook already warns about a missing Python 3, and a
# gate must never wedge pushes.
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
exec $PY "$DIR/push-gate.py"
