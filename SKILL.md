---
name: skill-audit
description: Audit an agent skills pack for duplicates, overlapping triggers, missing metadata and hygiene issues. Use when you inherit, merge, or maintain a folder of SKILL.md skills.
version: 0.1.0
---

# skill-audit

One command audits a folder of Agent Skills (`SKILL.md` files) for health problems: duplicate names, overlapping descriptions that fight over the same trigger, missing names/descriptions/frontmatter, invalid (non-kebab-case) names, thin bodies, and missing versions. Zero dependencies — Python 3.9+ standard library only.

## When to use

- You just inherited or merged a skills pack assembled from multiple sources.
- You added new skills and want to verify they don't collide with existing ones.
- Before publishing a skills pack: confirm every skill is discoverable and well-formed.
- After fixing flagged skills: re-run to confirm exit code 0.

## How to run

Install once:

```bash
pip install git+https://github.com/techdevfun/skill-audit.git
```

Then audit any pack folder:

```bash
skill-audit check --path <pack-folder>
```

No-install alternative (run from a clone of this repo):

```bash
PYTHONPATH=src python3 -m skill_audit check --path <pack-folder>
```

Read the findings:

- `[ERROR]` = must fix (duplicate name, missing description, invalid name...)
- `[WARN]` = should fix (no version, unparseable frontmatter...)
- Exit code `1` = errors found, `0` = clean.

Fix the flagged `SKILL.md` files, re-run until the exit code is 0.

## Checks performed

Duplicate name; invalid name (not kebab-case); missing name; missing description; missing frontmatter; duplicate or ≥70%-overlapping descriptions (Jaccard); description too short (<20 chars) or too long (>1024 chars); thin body (<50 chars); folders with files but no `SKILL.md`; missing `version`. See README.md for the full table.

## Examples

`examples/good/` is a clean pack (passes with exit code 0). `examples/messy/` is a broken pack demonstrating each finding — run the tool on it to see every error and warning the audit can produce.

## Guarantees

- **Read-only**: the tool never modifies your skills, it only reports.
- **No network, no telemetry, no dependencies**: everything runs locally with the Python standard library.
- MIT licensed. Also listed on Agensi (free): https://www.agensi.io/skills/skill-audit-agent-skills-pack-health-check
