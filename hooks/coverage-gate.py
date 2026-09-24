#!/usr/bin/env python3
"""PreToolUse(Bash) hook: enforce the SDD test-coverage gate on ``git commit``.

Why a hook and not just the ``/sdd:commit`` skill step: the skill step only runs
when the commit goes through ``/sdd:commit``. A raw ``git commit`` — or one with
``--no-verify`` — skips it entirely. This hook fires on the Bash *tool call*,
before git ever runs, so it cannot be ``--no-verify``'d.

Scope: only enforces when the *current branch* has its own active pipeline
state, so it never fires in non-SDD repos even though plugin hooks are global.
Deliberately branch-scoped rather than "any ``.specwork/`` present": that
directory is gitignored and survives `git checkout`, so it routinely still
holds another branch's pipeline state while you're on and committing to
something else entirely — that leftover state must never make this gate apply
here. Fails *open* on any internal error — a buggy gate must never wedge the
user's commits. The only blocking exit is code 2 (the PreToolUse "deny"
convention), and only for the one real signal: changed classes missing a test
on a branch with its own active, opted-in pipeline.

It reuses the pure functions in ``lib/coverage.py`` so the rule stays in one
place; this file only adds the tool-call detection and pipeline scoping.
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


def _segment_is_git_commit(segment):
    """True when a single shell segment invokes ``git commit`` as its subcommand.

    Skips git global options (and their args) so ``git -C path commit`` matches,
    while ``git log --grep=commit`` does not — we require ``commit`` to be the
    first non-option token after ``git``.
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
        return t == "commit"
    return False


def command_commits(cmd):
    """True when any segment of a compound command runs ``git commit``."""
    return any(_segment_is_git_commit(seg) for seg in _SEGMENT_SPLIT.split(cmd))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not command_commits(cmd):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    try:
        os.chdir(cwd)
    except Exception:
        pass

    # Cheap fast-path: no .specwork/ anywhere at all -> definitely no pipeline.
    if not os.path.isdir(".specwork"):
        return 0

    sys.path.insert(0, LIB)
    try:
        import coverage
        import gates
        import validation
    except Exception:
        return 0  # fail open — never wedge commits on an import error

    # Scope: only enforce when THIS branch has its own active pipeline state.
    # .specwork/ is gitignored and survives `git checkout`, so it commonly
    # still holds a *different* branch's leftover pipeline (e.g. this branch
    # was created for unrelated, non-pipeline work while another feature
    # branch's pipeline is still sitting on disk). That leftover state must
    # not make the coverage gate apply here — it's opt-in via /sdd:start, not
    # "whatever .specwork/ happens to contain." resolve_slug()'s "first state
    # file" fallback is right for skills resuming the current pipeline, but
    # wrong here; resolve_slug_for_branch() returns "" instead when nothing
    # matches, which both scopes the gate itself and (as before) keeps the
    # waiver lookup from adopting an unrelated branch's waivers.
    try:
        branch = validation.current_branch()
        slug = gates.resolve_slug_for_branch(branch) or None
    except Exception:
        slug = None

    if not slug:
        return 0

    try:
        stack = coverage._detect_stack()
        if stack not in ("java", "frontend"):
            return 0  # no convention to enforce for this stack
        offenders = coverage.classes_missing_tests(
            coverage.changed_files(),
            coverage.all_repo_files(),
            stack,
            waived=coverage.load_waivers(slug),
        )
    except Exception:
        return 0  # fail open on any gate error

    if not offenders:
        return 0

    waivers = coverage.waiver_paths(slug)
    waiver_file = waivers[0] if waivers else ".sdd-coverage-waivers.json"
    lines = [
        "✗ Blocked by SDD coverage gate (PreToolUse hook): "
        "{} changed class(es) lack a matching test:".format(len(offenders))
    ]
    lines += ["    - {}".format(o) for o in offenders]
    lines += [
        "",
        "Add a test for each, or waive a class with no testable surface in",
        "  {}".format(waiver_file),
        '  e.g. {{ "{}": "pure config, no testable logic" }}'.format(offenders[0]),
        "",
        "This hook fires on the Bash tool call, so `git commit --no-verify` cannot bypass it.",
    ]
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
