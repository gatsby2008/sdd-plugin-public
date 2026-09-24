#!/usr/bin/env bash
# Self-contained smoke test for the SDD pipeline in THIS repo (sdd-pipeline).
# Exercises the non-interactive cases: the unit suite, precheck against a real
# start state, and non-interactive flag resolution from state.json.
# Runs every scenario in an isolated scratch git repo. References nothing outside
# this repo.
set -uo pipefail

SDD="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # lib/tests -> lib -> sdd
export PYTHONPATH="$SDD"
PASS=0; FAIL=0
SCRATCH_ROOT="$(mktemp -d)"
trap 'rm -rf "$SCRATCH_ROOT"' EXIT

ok()  { printf '  \033[32mPASS\033[0m %s\n' "$1"; PASS=$((PASS+1)); }
bad() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }

assert_rc()  { local exp="$1" label="$2"; shift 3; local out rc
  out="$("$@" 2>&1 </dev/null)"; rc=$?
  if [ "$rc" -eq "$exp" ]; then ok "$label (rc=$rc)"; else bad "$label (rc=$rc, want $exp) :: ${out:0:120}"; fi; }
assert_out() { local sub="$1" label="$2"; shift 3; local out
  out="$("$@" 2>&1 </dev/null)"
  if printf '%s' "$out" | grep -qF "$sub"; then ok "$label"; else bad "$label (missing '$sub') :: ${out:0:160}"; fi; }
new_repo() { local d="$SCRATCH_ROOT/$1"; mkdir -p "$d"; ( cd "$d" && git init -q && git commit -q --allow-empty -m init && git checkout -q -b feature/demo ); echo "$d"; }

echo "== unit suite =="
( cd "$SDD" && python3 -m unittest discover -s lib/tests -p 'test_*.py' >/dev/null 2>&1 ) \
  && ok "unittest suite" || bad "unittest suite"

echo "== precheck =="
d=$(new_repo precheck-none); cd "$d"
assert_rc 1 "no .specwork rejects" -- python3 "$SDD/lib/gates.py" precheck
assert_out "Run /sdd:start first" "rejection message" -- python3 "$SDD/lib/gates.py" precheck
d=$(new_repo precheck-empty); cd "$d"; mkdir -p .specwork/_state
assert_rc 1 "empty .specwork rejects" -- python3 "$SDD/lib/gates.py" precheck

echo "== precheck against real start state =="
d=$(new_repo status); cd "$d"
python3 "$SDD/lib/start.py" --slug demo --ticket PROJ-1 --input-type jira --branch feature/demo --base-branch main >/dev/null 2>&1
assert_rc 0  "precheck initialized passes" -- python3 "$SDD/lib/gates.py" precheck
assert_rc 0  "precheck known slug passes" -- python3 "$SDD/lib/gates.py" precheck demo
assert_rc 1  "precheck unknown slug rejects" -- python3 "$SDD/lib/gates.py" precheck nope
assert_out "0" "non-interactive defaults to 0 when not set" -- python3 "$SDD/lib/gates.py" non-interactive demo

echo "== non-interactive from state.json =="
printf '{"id":"demo","ticket_type":"feature","input_type":"jira","non_interactive":true}' > .specwork/_state/demo-state.json
assert_out "1" "non-interactive reads from state.json" -- python3 "$SDD/lib/gates.py" non-interactive demo

echo "------------------------------------------------------------------"
printf " RESULT: %d passed, %d failed\n" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
