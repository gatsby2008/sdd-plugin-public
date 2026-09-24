#!/usr/bin/env python3
"""SessionStart hook: surface a compact SDD pipeline status when one is active.

Awareness, not enforcement. On session start (startup / resume / clear), if the
current branch has an active pipeline (``.specwork/``), print a short orientation
block — branch, slug, spec/plan state, open-question count, and the next step —
so the model and the developer pick up where they left off. SessionStart stdout
is added to the session context, so this is the cheapest way to keep the agent
oriented without paying a per-prompt token cost (the UserPromptSubmit alternative).

Silent in non-SDD repos: prints nothing unless ``.specwork/`` resolves a slug, so
this global hook never adds noise outside the pipeline. Fails open (exit 0) on any
error — a status line must never wedge a session. Config validation (jira/mr) is
intentionally omitted: both have sane defaults (jira is optional for free-text
flows; mr defaults to ``development``), so warning about their absence would be noise.

The next-step logic mirrors the pipeline's own early gates (Open Questions, plan
staleness) so it never contradicts /sdd:state; past ``/sdd:implement`` it defers
to /sdd:state rather than guess at post-implement state.
"""
import json
import os
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(HOOK_DIR))
LIB = os.path.join(PLUGIN_ROOT, "lib")


def _current_branch():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def compute_status(slug, gates, paths):
    """Filesystem-derived snapshot for ``slug`` (spec/plan/OQs/staleness/next)."""
    import os.path as op

    spec_path = paths.spec_file(slug)
    plan_path = paths.plan_file(slug)
    spec_exists = op.isfile(spec_path)
    plan_exists = op.isfile(plan_path)

    open_n = resolved_n = 0
    if spec_exists:
        try:
            with open(spec_path, encoding="utf-8") as fh:
                open_n, resolved_n = gates.count_open_questions(fh.read())
        except Exception:
            pass

    stale = False
    if plan_exists:
        try:
            r = gates.check_plan_staleness(slug)
            stale = bool(r and r.get("stale"))
        except Exception:
            pass

    if not spec_exists:
        nxt, hint = "/sdd:spec", "draft the spec"
    elif open_n > 0:
        nxt, hint = "/sdd:spec", "resolve {} open question{}".format(
            open_n, "" if open_n == 1 else "s"
        )
    elif not plan_exists:
        nxt, hint = "/sdd:plan", "optional · or /sdd:implement"
    elif stale:
        nxt, hint = "/sdd:plan", "plan is stale"
    else:
        nxt, hint = "/sdd:implement", ""

    return {
        "spec_exists": spec_exists,
        "plan_exists": plan_exists,
        "open": open_n,
        "resolved": resolved_n,
        "stale": stale,
        "next": nxt,
        "hint": hint,
    }


def render(branch, slug, st):
    """Compact multi-line status block."""
    if st["spec_exists"]:
        spec = "spec ✓ · {} open / {} resolved OQs".format(st["open"], st["resolved"])
    else:
        spec = "spec ✗ (not drafted)"
    if not st["spec_exists"]:
        plan = ""
    elif st["plan_exists"]:
        plan = " · plan " + ("⚠ stale" if st["stale"] else "✓")
    else:
        plan = " · plan ✗"
    nxt = "next → {}{}".format(st["next"], " ({})".format(st["hint"]) if st["hint"] else "")
    branch_label = branch or "(detached)"
    return "\n".join(
        [
            "🔎 SDD pipeline active · {} (slug: {})".format(branch_label, slug),
            "   {}{}".format(spec, plan),
            "   {}   |   /sdd:state for detail".format(nxt),
        ]
    )


def main():
    # SessionStart provides a payload (source, cwd, …); tolerate its absence.
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    cwd = data.get("cwd") or os.getcwd()
    try:
        os.chdir(cwd)
    except Exception:
        pass

    if not os.path.isdir(".specwork/_state"):
        return 0

    sys.path.insert(0, LIB)
    try:
        import gates
        import paths
    except Exception:
        return 0

    try:
        branch = _current_branch()
        slug = gates.resolve_slug(branch or None)
        if not slug:
            return 0
        st = compute_status(slug, gates, paths)
        sys.stdout.write(render(branch, slug, st) + "\n")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
