# Skill Structure Template

Every skill in the SDD pipeline has two required files:

## 1. SKILL.md (Specification for the Agent)

This is what the agent reads when executing the skill.

```markdown
---
name: example
description: One-line description of what this skill does
argument-hint: "[optional-arg]"
allowed-tools: Read, Write, Bash(git status:*), Bash(cat .specwork/_spec/*)
---

# Skill Name

Short intro: what this skill does and why.

---

## Core Rule (optional)

Key constraint or non-negotiable behavior.

---

## Use Cases

Show how to invoke it:
```bash
/sdd:example
/sdd:example PROJ-123
```

---

## What It Does

| Step | Action |
|------|--------|
| 1 | Detect branch |
| 2 | Load artifacts |
| 3 | Process |
| 4 | Output result |

---

## Step Details

### Step 1 — Detect Branch

```bash
git rev-parse --abbrev-ref HEAD
```

Details...

---

## Rules

- Rule 1: Focused behavior
- Rule 2: No broad scans
- Rule 3: Fail cleanly on missing artifacts

---

## Requirements

- Working branch active
- Required artifacts must exist

---

## Related Skills

- `start` — creates initial artifacts
- `spec` — drafts and refines the spec
- `commit` — records changes
```

**Key sections:**
- Frontmatter (name, description, allowed-tools)
- Short intro
- Use cases (invocation examples)
- What It Does (step table)
- Step Details (step-by-step breakdown)
- Rules (hard constraints)
- Requirements (preconditions)
- Related Skills (dependencies)

---

## 2. README.md (User Documentation)

This is what users read to understand when and how to use the skill.

```markdown
# Skill Name

One-sentence summary of what it does.

Longer explanation: when to use, what problem it solves.

---

## Prerequisites

- Feature branch active
- Required artifacts (list them)
- Optional: external tools (glab, etc.)

---

## Usage

```bash
/sdd:example
/sdd:example explicit-arg
```

---

## What It Does

High-level description of the process (not step-by-step).

Example output or behavior.

---

## When to Use

Scenarios where this skill is the right choice.

---

## Output / Next Step

What the skill produces and what you do next.

---

## Troubleshooting

**Problem 1**
Solution.

**Problem 2**
Solution.

---

## Related Skills

- `/sdd:spec` — drafts and refines the spec
- `/sdd:commit` — records progress
```

**Key sections:**
- Title + one-line summary
- What it does (user perspective, not agent)
- Prerequisites
- Usage (how to invoke)
- When to use
- Output/next step
- Troubleshooting
- Related skills

---

## Relationship Between SKILL.md and README.md

| Audience | File | Focus |
|----------|------|-------|
| **Agent** | SKILL.md | Execution logic, rules, step-by-step algorithm |
| **User** | README.md | When to use, how to invoke, what happens |

**SKILL.md** is technical/prescriptive (agent instructions).
**README.md** is practical/user-focused (what does it do for me).

---

## Example Files

See `status/` for a simple skill:
- `status/SKILL.md` — small, focused spec
- `status/README.md` — clear user guide

See `implement/` for a complex skill:
- `implement/SKILL.md` — detailed step breakdown
- `implement/README.md` — workflow patterns explained
