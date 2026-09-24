#!/usr/bin/env bash
# PostToolUse(Bash) hook entrypoint: remind to re-key .specwork/ after a branch
# change (see resync-reminder.py). This fires after *every* Bash tool call, so it
# does a cheap shell pre-filter first — only payloads that mention a branch verb
# (checkout/switch/branch) pay the cost of starting Python. Everything else exits
# immediately. Fails open (exit 0) when no interpreter is found; a reminder must
# never disrupt work.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Slurp the JSON payload once so we can both pre-filter and forward it.
PAYLOAD="$(cat)"
case "$PAYLOAD" in
  *checkout*|*switch*|*branch*) : ;;   # might be a branch change → check properly
  *) exit 0 ;;                          # no branch verb → definitely nothing to do
esac

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
exec $PY "$DIR/resync-reminder.py" <<<"$PAYLOAD"
