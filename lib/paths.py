"""Canonical `.specwork` artifact paths, derived from a slug.

Single source of truth for the artifact layout so skills and lib modules stop
hardcoding `.specwork/_state/<slug>-state.json` etc. (previously duplicated as
prose/shell across 10+ skills). Paths are returned as POSIX strings to match the
values written into state.json and keep output stable across platforms.
"""
from pathlib import PurePosixPath

DEFAULT_SPEC_DIR = ".specwork"


def _p(spec_dir, sub, name):
    return (PurePosixPath(spec_dir) / sub / name).as_posix()


def state_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_state", f"{slug}-state.json")


def rules_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_state", f"{slug}-rules.json")


def cache_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_state", f"{slug}-implementation-cache.json")


def path_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_state", f"{slug}-path.json")


def spec_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_spec", f"{slug}-spec.md")


def source_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_spec", f"{slug}-source.md")


def plan_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_plan", f"{slug}-plan.md")


def context_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    return _p(spec_dir, "_progress", f"{slug}-context.md")


def validated_file(slug, spec_dir=DEFAULT_SPEC_DIR):
    """Marker stamping the HEAD sha that last passed `commands/check.sh`.

    Written by /sdd:mr after a green Pre-Push Validation; read by the
    PreToolUse(git push) hook so it can enforce the quality gate cheaply
    (compare HEAD vs the stamped sha) instead of re-running the full suite.
    Not part of `all_paths` — it is created at push time, not by /sdd:start.
    """
    return _p(spec_dir, "_state", f"{slug}-validated.json")


def all_paths(slug, spec_dir=DEFAULT_SPEC_DIR):
    """Every artifact path for a slug, keyed by the name used in state.json."""
    return {
        "state_file": state_file(slug, spec_dir),
        "rules_file": rules_file(slug, spec_dir),
        "cache_file": cache_file(slug, spec_dir),
        "path_file": path_file(slug, spec_dir),
        "spec_file": spec_file(slug, spec_dir),
        "source_file": source_file(slug, spec_dir),
        "plan_file": plan_file(slug, spec_dir),
        "context_file": context_file(slug, spec_dir),
    }
