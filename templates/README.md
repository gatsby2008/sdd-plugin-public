# Templates

Configuration and scaffold templates for SDD pipeline projects. Not a skill itself — these are templates copied into consumer projects.

## Rule sources used by the SDD pipeline

- `${CLAUDE_PLUGIN_ROOT}/AGENTS.md` contains shared pipeline rules: execution, safety, state usage, and testing behavior.
- `service-rules.md` in this folder is a scaffold for project-specific invariants. Consumer projects should copy it to `./.claude/service-rules.md` and tailor it there.

## How they work together

When `/sdd:start` runs, it:

1. reads the shared rules from `${CLAUDE_PLUGIN_ROOT}/AGENTS.md`
2. reads `./.claude/service-rules.md` from the active project if it exists
3. scaffolds `./.claude/service-rules.md` from this template when it is missing
4. writes both sources into `.specwork/_state/<slug>-rules.json` for downstream skills

Downstream skills should consume `rules.json` instead of re-reading the markdown files.

## Precedence

- Project-local `./.claude/service-rules.md` is the active service rule source.
- This template is only for initial scaffold.
- There is no automatic merge between the template and a project-local `service-rules.md`.

