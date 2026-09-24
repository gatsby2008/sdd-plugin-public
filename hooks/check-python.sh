#!/usr/bin/env bash
# SessionStart hook: the SDD pipeline shells out to `python3`. This verifies an
# interpreter is reachable and, when only `python`/`py` exist (Windows + Git Bash),
# drops a `python3` shim into ~/.claude/bin. Quiet on success; never fails.
set -uo pipefail

CLAUDE_DIR="${HOME}/.claude"

command -v python3 >/dev/null 2>&1 && exit 0

alt=""
if command -v python >/dev/null 2>&1 \
   && python -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then
  alt="python"
elif command -v py >/dev/null 2>&1 && py -3 -c "" 2>/dev/null; then
  alt="py -3"
fi

if [ -z "$alt" ]; then
  echo "[sdd] Python 3 not found (looked for python3, python, py). The SDD pipeline needs it — install Python 3 or use WSL2." >&2
  exit 0
fi

mkdir -p "$CLAUDE_DIR/bin"
cat > "$CLAUDE_DIR/bin/python3" <<SHIM
#!/usr/bin/env bash
exec $alt "\$@"
SHIM
chmod +x "$CLAUDE_DIR/bin/python3"
echo "[sdd] Created a python3 shim at $CLAUDE_DIR/bin/python3 — add \$HOME/.claude/bin to your PATH." >&2
exit 0
