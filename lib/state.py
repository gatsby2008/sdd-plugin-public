#!/usr/bin/env python3
"""Read/patch SDD ``state.json`` files.

`build_state` (initial creation) lives in start.py; this module covers reading
and patching an existing state file — notably the resync slug/branch rename,
previously an inline python heredoc.

CLI:
  python3 state.py get <state_path> <key>
  python3 state.py set <state_path> <key> <value>
  python3 state.py rename-slug <state_path> <new_slug> <old_slug> <branch> <ticket> <input_type>
"""
import json
import sys
from pathlib import Path


def load_state(state_path):
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def update_state_field(state_path, key, value):
    """Patch a single field; returns the updated dict."""
    p = Path(state_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    d[key] = value
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    return d


def rename_slug(state_path, new_slug, old_slug, branch, ticket, input_type):
    """Rewrite a state.json for a slug/branch rename (resync Step 7).

    First replaces ``old_slug``→``new_slug`` in every string field (internal
    paths), then sets the authoritative id/branch/ticket/input_type. Replacement
    runs first so a new slug that contains the old one (e.g.
    ``consent`` → ``ir-70-consent``) doesn't double-up. ``source_title`` is left
    untouched. Returns the updated dict.
    """
    p = Path(state_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    for k, v in list(d.items()):
        if isinstance(v, str) and old_slug in v:
            d[k] = v.replace(old_slug, new_slug)
    d["id"] = new_slug
    d["branch"] = branch
    d["ticket"] = ticket if ticket else None
    d["input_type"] = input_type
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    return d


def _main(argv):
    if len(argv) < 2:
        print("Usage: state.py <get|set|rename-slug> <state_path> [args]")
        sys.exit(2)
    cmd, path = argv[0], argv[1]
    if cmd == "get":
        print(load_state(path).get(argv[2]))
    elif cmd == "set":
        update_state_field(path, argv[2], argv[3])
    elif cmd == "rename-slug":
        new_slug, old_slug, branch, ticket, input_type = argv[2:7]
        rename_slug(path, new_slug, old_slug, branch, ticket, input_type)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
