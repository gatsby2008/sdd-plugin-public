#!/usr/bin/env python3
"""PreToolUse(Bash) hook: enforce the SDD quality gate on ``git push``.

Why a hook and not just the ``/sdd:mr`` step: the skill step only runs when the
push goes through ``/sdd:mr``. A raw ``git push`` — or ``/sdd:commit``'s push
offer — skips ``commands/check.sh`` entirely. This hook fires on the Bash *tool
call*, before git runs, so it cannot be bypassed by pushing manually through the
agent.

Cost: ``check.sh`` runs the full suite (minutes), which would blow the hook
timeout and double the build ``/sdd:mr`` already ran. So this hook does NOT run
check.sh — it enforces a cheap invariant instead: ``HEAD`` must equal the sha
that last passed check.sh, stamped into ``.specwork/_state/<slug>-validated.json``
by ``lib/validation.py`` (called from ``/sdd:mr`` after a green Pre-Push
Validation). The hook just compares the two.

Scope: only when a pipeline's state.json ``branch`` field exactly matches the
branch being pushed, and only when the project actually defines
``commands/check.sh`` — there is no gate to enforce otherwise, so it no-ops.
Deliberately branch-scoped rather than "any ``.specwork/`` present": that
directory is gitignored and survives `git checkout`, so it routinely still
holds another branch's pipeline state (a feature branch mid-review, say) while
you're on and pushing something else entirely — that leftover state must never
gate an unrelated push. Fails *open* on any internal error; the only blocking
exit is code 2 (the PreToolUse "deny" convention), and only for the one real
signal: a push on a branch with its own active, unvalidated pipeline.
"""
import json
import os
import re
import shlex
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(HOOK_DIR))
LIB = os.path.join(PLUGIN_ROOT, "lib")

# git global options that consume the following token as their argument.
_GIT_OPT_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# command separators that start a new shell command segment.
_SEGMENT_SPLIT = re.compile(r"\|\||&&|[;&|\n]")

# push flags that mean "this push sends no new code to validate" → don't gate.
_NON_CODE_PUSH_FLAGS = {"--delete", "-d", "--dry-run", "--tags"}


def _segment_is_git_push(segment):
    """True when a single shell segment invokes ``git push`` (with code to send).

    Skips git global options (and their args) so ``git -C path push`` matches,
    while ``git log --grep=push`` does not — ``push`` must be the first
    non-option token after ``git``. Pushes that send no code to validate
    (``--delete``, ``--dry-run``, tag-only ``--tags``) are treated as non-pushes.
    """
    try:
        toks = shlex.split(segment)
    except ValueError:
        toks = segment.split()
    if "git" not in toks:
        return False
    j = toks.index("git") + 1
    while j < len(toks):
        t = toks[j]
        if t in _GIT_OPT_WITH_ARG:
            j += 2
            continue
        if t.startswith("-"):
            j += 1
            continue
        if t != "push":
            return False
        # It's a push — bail out if it carries a non-code flag.
        rest = toks[j + 1 :]
        return not any(f in _NON_CODE_PUSH_FLAGS for f in rest)
    return False


def command_pushes(cmd):
    """True when any segment of a compound command runs a code-bearing ``git push``."""
    return any(_segment_is_git_push(seg) for seg in _SEGMENT_SPLIT.split(cmd))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not command_pushes(cmd):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    try:
        os.chdir(cwd)
    except Exception:
        pass

    # Scope: only enforce inside an active SDD pipeline...
    if not os.path.isdir(".specwork"):
        return 0
    # ...and only when the project actually defines a quality gate to enforce.
    if not os.path.isfile(os.path.join("commands", "check.sh")):
        return 0

    sys.path.insert(0, LIB)
    try:
        import gates
        import validation
    except Exception:
        return 0  # fail open — never wedge pushes on an import error

    # Resolve the pipeline slug strictly for THIS branch — .specwork/ is
    # gitignored and survives `git checkout`, so it commonly still holds
    # another branch's pipeline state (e.g. an in-review feature branch)
    # while you're pushing something unrelated. gates.resolve_slug() falls
    # back to "the first state file" when nothing matches, which would wrongly
    # gate this push against a pipeline that has nothing to do with it.
    # resolve_slug_for_branch() returns "" instead — nothing to gate here.
    try:
        branch = validation.current_branch()
        slug = gates.resolve_slug_for_branch(branch) or None
    except Exception:
        slug = None

    if not slug:
        return 0

    try:
        if validation.is_valid(slug):
            return 0
    except Exception:
        return 0  # fail open on any gate error

    lines = [
        "✗ Blocked by SDD quality gate (PreToolUse hook): HEAD has not passed "
        "`commands/check.sh`.",
        "",
        "Active pipeline for this branch: {}".format(slug),
        "",
        "Push through /sdd:mr (it runs check.sh, then pushes), or validate manually:",
        "    bash commands/check.sh && \\",
        "      python3 ${CLAUDE_PLUGIN_ROOT}/lib/validation.py record",
        "then retry the push.",
        "",
        "If this pipeline isn't what you're pushing right now, clear it instead:",
        "    /sdd:pause   — stash the pipeline state to resume later",
        "    /sdd:close   — wipe it if the work is merged or abandoned",
        "",
        "This hook fires on the Bash tool call, so it cannot be bypassed by pushing "
        "manually through the agent.",
    ]
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
