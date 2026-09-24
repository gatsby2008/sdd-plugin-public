# Migrating a symlink-based skills repo to a Claude Code plugin

How this repo (`sdd`) went from a **symlink-based** Claude Code skills
distribution to a **self-contained plugin**. Keep it as a checklist if you ever
convert another skills bundle.

## Before vs after

| | Symlink distribution | This plugin |
|---|---|---|
| Install | a shell installer symlinks each skill into `~/.claude/skills/` | `/plugin install sdd@gatsby` |
| Commands | flat (`/f-start`, `/f-spec`, …) | namespaced (`/sdd:start`, `/sdd:spec`, …) |
| Updates | `git pull` + re-run the installer | `/plugin update sdd` |
| Maintenance | you maintain the installer + Windows parity | handled natively by Claude Code |

The conversion was done on a **copy** of the symlink repo, leaving the original
intact as a fallback.

## The 4 structural changes

### 1. Flatten skills — discovery is one level deep
Plugin skill discovery only sees `skills/<name>/SKILL.md`. Nested bundles such as
`skills/sdd/start/SKILL.md` are **not** discovered. So:

- every skill moved up to `skills/<name>/` (35 flat skills)
- the `name:` in each `SKILL.md` frontmatter must equal its directory name
- shared assets (`lib/`, `templates/`, `docs/`) moved to the repo root

### 2. Reference shared assets via `${CLAUDE_PLUGIN_ROOT}`
A symlink install lets skills reach helpers at a fixed `~/.claude/...` path; a
plugin does not. Every runtime reference now uses the plugin variable:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/start.py"
```

`${CLAUDE_PLUGIN_ROOT}` points at the installed plugin root and is available both
in the Bash commands a skill runs and in hooks.

### 3. Namespacing is mandatory
Plugin commands are always `/<plugin>:<skill>` — there is no way to keep flat
names. So `/f-start` → `/sdd:start`. We also dropped the now-redundant `f-`
prefix (the `sdd:` namespace already conveys it): `/f-mr-review` → `/sdd:mr-review`.
Agents may nest, and the path becomes part of the name —
`agents/java/quality-reviewer.md` registers as `sdd:java:quality-reviewer`.

### 4. Plugin scaffolding replaces the installer
- `.claude-plugin/plugin.json` — the manifest (`name`, `description`, `version`)
- `.claude-plugin/marketplace.json` — lets users `/plugin marketplace add <git-url>`
- `hooks/hooks.json` — a `SessionStart` hook took over the Python 3 check the old
  installer ran post-install (plugins have no post-install step)
- the old install/uninstall shell scripts were removed — `/plugin` does that now

## Gotchas worth remembering
- **Do not also declare `hooks` in `plugin.json` when you ship `hooks/hooks.json`.**
  The standard `hooks/hooks.json` auto-loads; declaring it again is a
  duplicate-load error at startup.
- **Skill basenames must be unique across the whole plugin** — they all share the
  single `sdd:` prefix, so two skills with the same basename collide.
- Internal script filenames can be anything, but we renamed `lib/f-start.py` →
  `lib/start.py` (and similar) so nothing carries the old prefix.
- A `SessionStart` hook should be **quiet on success** — it runs every session.

## Self-containment
This repo must not reference its origin or any sibling variant. A test
(`lib/tests/test_self_contained.py`, part of the unit suite) fails the build if a
forbidden token reappears anywhere in the tree.

## Testing the conversion
```bash
# load it without installing anything permanent
claude --plugin-dir /path/to/this/repo
# then inside: /plugin (lists sdd), /sdd:whatnext

# run the unit suite
cd lib && python3 -m unittest discover -s tests
```
