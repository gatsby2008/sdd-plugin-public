#!/usr/bin/env python3
"""PreToolUse(Edit|Write) hook: warn before editing when .specwork/ isn't ours.

``.specwork/`` is gitignored, so it survives ``git checkout`` and routinely still
holds a *different* branch's pipeline. The ``/sdd:*`` skills each check ownership
before acting, and the SessionStart banner reports a mismatch when the session
opens — but plain file edits go through neither. This closes that last path: the
first time code is changed on a branch whose pipeline isn't its own, say so.

Awareness, not enforcement. It never blocks: editing files on a branch with a
foreign ``.specwork/`` is perfectly legitimate work (a hotfix, an unrelated
issue) — the point is that the developer decides what happens to the *other*
pipeline (``/sdd:pause`` / ``/sdd:close``) instead of leaving it to be adopted by
accident later.

Fires at most once per (session, branch, pipeline). The trigger is a state you
sit in, not an event you repeat, so warning on every Edit would be noise; the
marker lives under ``$CLAUDE_PLUGIN_DATA`` (plugin-private state — never
``~/.claude``). Switching branches, or a different pipeline landing on disk,
arms it again. Fails open (exit 0) on any error.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(HOOK_DIR))
LIB = os.path.join(PLUGIN_ROOT, "lib")

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")

# Markers older than this are swept on the way past — a session id is never
# reused, so without a sweep the directory would grow forever.
MARKER_TTL_SECONDS = 7 * 24 * 60 * 60


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


def _repo_root():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return os.getcwd()


def marker_dir():
    """Plugin-private scratch dir for the once-per-session markers.

    ``$CLAUDE_PLUGIN_DATA`` is the sanctioned location; the temp-dir fallback
    keeps the hook working when it is unset (dedup then lasts as long as the
    temp dir does, which is fine — the marker is a nicety, not state anyone
    depends on). Never writes to ``~/.claude``.
    """
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        tempfile.gettempdir(), "sdd-plugin"
    )
    return os.path.join(base, "branch-mismatch-warn")


def marker_path(session_id, repo, branch, slug):
    """One marker per (session, repo, branch, pipeline).

    Hashed because branch names carry ``/`` and slugs are user-supplied; the
    inputs are identity, not secrets, so a short digest is enough.
    """
    key = "|".join([session_id or "-", repo or "-", branch or "-", slug or "-"])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(marker_dir(), digest)


def already_warned(path):
    return os.path.exists(path)


def record_warned(path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(int(time.time())))
    except Exception:
        pass  # dedup is best-effort; a repeated warning beats a crashed hook


def sweep_stale_markers(now=None):
    """Delete markers past their TTL. Best-effort, never raises."""
    now = time.time() if now is None else now
    directory = marker_dir()
    try:
        names = os.listdir(directory)
    except Exception:
        return
    for name in names:
        path = os.path.join(directory, name)
        try:
            if now - os.path.getmtime(path) > MARKER_TTL_SECONDS:
                os.remove(path)
        except Exception:
            continue


def build_message(branch, status):
    """The warning. Names the other pipeline and the two ways to resolve it."""
    slug = status.get("slug") or "?"
    recorded = status.get("recorded_branch") or "?"
    here = "a detached HEAD" if branch == "HEAD" else "'{}'".format(branch or "?")
    return "\n".join(
        [
            "⚠️ SDD: you are editing files on {}, but .specwork/ holds the "
            "pipeline for '{}' (slug '{}').".format(here, recorded, slug),
            ".specwork/ is gitignored, so it did not move when the branch changed.",
            "Nothing is blocked — these edits are treated as standalone work: no "
            "spec, no plan, and /sdd:commit and /sdd:mr will not use '{}'s "
            "artifacts.".format(slug),
            "  • /sdd:pause  — stash '{}' to resume it later (its MR is still "
            "open)".format(slug),
            "  • /sdd:close  — clear it (its MR merged, or the work was "
            "abandoned)",
            "  • /sdd:start  — begin a pipeline for {} instead".format(here),
        ]
    )


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in EDIT_TOOLS:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    try:
        os.chdir(cwd)
    except Exception:
        pass

    # Scope: only where a pipeline exists at all. Non-SDD repos pay nothing.
    if not os.path.isdir(".specwork/_state"):
        return 0

    sys.path.insert(0, LIB)
    try:
        import gates
    except Exception:
        return 0

    try:
        branch = _current_branch()
        status = gates.pipeline_branch_status(branch)

        # Ours → nothing to say. None at all → standalone, a first-class flow.
        # On the pipeline's own base_branch → the post-merge cleanup spot where
        # /sdd:close is meant to run, so not a mismatch either.
        if status["owns_pipeline"] or not status["has_any_pipeline"]:
            return 0
        if status["is_base_branch"]:
            return 0

        path = marker_path(
            data.get("session_id", ""), _repo_root(), branch, status["slug"]
        )
        if already_warned(path):
            return 0
        record_warned(path)
        sweep_stale_markers()
        msg = build_message(branch, status)
    except Exception:
        return 0  # never disrupt an edit — a warning is not worth an error

    # systemMessage warns without the "blocked" framing of exit 2. The edit is
    # legitimate; only the leftover pipeline needs a decision.
    sys.stdout.write(json.dumps({"systemMessage": msg}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
