"""Branch-name → slug / ticket / input-type derivation.

Single source of truth for logic previously duplicated as prose/embedded python
across start, status, close, help, resync, commit and handoff.
"""
import re

_PREFIX_RE = re.compile(r"^(feature|hotfix|release|bugfix)/")
# Strict: canonical Jira keys (IR-70, PROJ-1234) — queryable via the JIRA API.
_STRICT_TICKET_RE = re.compile(r"^([A-Z]+-[0-9]+)(?:-|$)")
# Loose: dotted variants (IR-70.1) — not API-queryable, but preserve user intent.
_LOOSE_TICKET_RE = re.compile(r"^([A-Z]+-[0-9.]+)(?:-|$)")


def strip_branch_prefix(branch):
    """Drop a leading feature/ hotfix/ release/ bugfix/ segment."""
    return _PREFIX_RE.sub("", branch)


def normalize_slug(text):
    """Lowercase, non-alphanumeric → hyphen, collapse runs, trim ends."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def slug_from_branch(branch):
    """Derive the pipeline slug from a branch name."""
    return normalize_slug(strip_branch_prefix(branch))


def ticket_from_branch(branch):
    """Return ``(ticket, input_type)``.

    Strict canonical Jira key → ``(KEY, "jira")``; loose dotted variant →
    ``(KEY, "freetext")``; no match → ``("", "freetext")``.
    """
    unprefixed = strip_branch_prefix(branch).upper()
    strict = _STRICT_TICKET_RE.match(unprefixed)
    if strict:
        return strict.group(1), "jira"
    loose = _LOOSE_TICKET_RE.match(unprefixed)
    if loose:
        return loose.group(1), "freetext"
    return "", "freetext"


def resolve_branch(branch):
    """Everything derivable from a branch name, in one call."""
    ticket, input_type = ticket_from_branch(branch)
    return {
        "branch": branch,
        "unprefixed": strip_branch_prefix(branch),
        "slug": slug_from_branch(branch),
        "ticket": ticket,
        "input_type": input_type,
    }


def _main(argv):
    """CLI: print resolve_branch(...) as JSON so skills can consume it from bash.

    Branch defaults to the current git branch when no argument is given.
    """
    import json
    import subprocess

    if argv:
        branch = argv[0]
    else:
        try:
            branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                .decode()
                .strip()
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise SystemExit("error: not a git repository (or git not found)")
    print(json.dumps(resolve_branch(branch), indent=2))


if __name__ == "__main__":
    import sys

    _main(sys.argv[1:])
