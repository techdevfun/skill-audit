"""Core audit logic for skill-audit. Standard library only.

A "skill" is a directory containing a SKILL.md file. The SKILL.md starts
with YAML-like frontmatter between two --- lines, e.g.:

    ---
    name: code-review
    description: Review a pull request for bugs, security issues and tests.
    ---

We parse that frontmatter without PyYAML on purpose: the tool must stay
zero-dependency so it runs anywhere Python runs.
"""

from __future__ import annotations

import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
WORD_RE = re.compile(r"[a-z0-9]+")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, list[str]]:
    """Parse SKILL.md frontmatter. Returns (fields, body, parse_warnings)."""
    warnings: list[str] = []
    if not text.startswith("---"):
        return {}, text, ["missing frontmatter block (file must start with ---)"]
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text, ["unclosed frontmatter block (missing closing ---)"]
    raw = parts[1]
    body = parts[2]
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        # Continuation of a folded (>) or literal (|) block: indented line.
        if line[:1] in (" ", "\t") and current_key is not None:
            fields[current_key] += " " + line.strip()
            continue
        if ":" not in line:
            warnings.append(f"ignoring frontmatter line without ':': {line[:80]!r}")
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip a single pair of quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        # Folded/literal indicator: value continues on indented lines.
        if value in (">", "|", ">-", "|-"):
            value = ""
        fields[key] = value
        current_key = key
    return fields, body, warnings


def tokens(text: str) -> set[str]:
    """Lowercased word tokens, dropping very short words (mostly stopwords)."""
    return {w for w in WORD_RE.findall(text.lower()) if len(w) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def discover_skills(root: Path) -> tuple[list[dict], list[dict]]:
    """Find all SKILL.md files under root. Returns (skills, issues)."""
    skills: list[dict] = []
    issues: list[dict] = []
    if not root.exists():
        return skills, [{"severity": "error", "code": "missing-dir",
                         "message": f"Directory not found: {root}", "skill": None}]
    skill_files = sorted(root.rglob("SKILL.md"))
    if not skill_files:
        return skills, [{"severity": "error", "code": "no-skills",
                         "message": f"No SKILL.md found under {root}", "skill": None}]
    for f in skill_files:
        # Skip vendored / generated dirs.
        if any(part in {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"} for part in f.parts):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        fields, body, warnings = parse_frontmatter(text)
        skill = {
            "path": str(f),
            "dir": str(f.parent),
            "name": fields.get("name"),
            "description": fields.get("description"),
            "version": fields.get("version"),
            "body_len": len(body.strip()),
        }
        skills.append(skill)
        for w in warnings:
            issues.append({"severity": "warning", "code": "frontmatter-parse",
                           "message": f"{f}: {w}", "skill": skill["name"] or f.parent.name})
        if skill["body_len"] < 50:
            issues.append({"severity": "warning", "code": "thin-body",
                           "message": f"{skill['name'] or f.parent.name}: SKILL.md body is very short "
                                      f"({skill['body_len']} chars). A skill needs real instructions, not just a header.",
                           "skill": skill["name"] or f.parent.name})
    # Directories that look like skill dirs but have no SKILL.md.
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name.startswith("."):
            continue
        if not (d / "SKILL.md").exists() and any(p.is_file() for p in d.iterdir()):
            issues.append({"severity": "warning", "code": "missing-skill-md",
                           "message": f"{d.name}: directory has files but no SKILL.md — "
                                      "agents will not discover it as a skill.", "skill": d.name})
    return skills, issues


def audit(root: Path) -> dict:
    skills, issues = discover_skills(root)

    seen_names: dict[str, str] = {}
    seen_descs: dict[str, str] = {}
    for s in skills:
        label = s["name"] or f"(unnamed in {s['dir']})"
        # Name checks.
        if not s["name"]:
            issues.append({"severity": "error", "code": "missing-name",
                           "message": f"{s['path']}: frontmatter has no 'name'.",
                           "skill": s["dir"]})
        elif not NAME_RE.match(s["name"]):
            issues.append({"severity": "error", "code": "invalid-name",
                           "message": f"{label!r}: name must be kebab-case "
                                      f"(lowercase letters, digits, hyphens), got {s['name']!r}.",
                           "skill": s["name"]})
        elif len(s["name"]) > 64:
            issues.append({"severity": "warning", "code": "name-too-long",
                           "message": f"{label!r}: name is {len(s['name'])} chars (keep under 64).",
                           "skill": s["name"]})
        if s["name"]:
            if s["name"] in seen_names:
                issues.append({"severity": "error", "code": "duplicate-name",
                               "message": f"Duplicate skill name {s['name']!r}: "
                                          f"{seen_names[s['name']]} and {s['path']}. "
                                          "The agent cannot tell which one to use.",
                               "skill": s["name"]})
            else:
                seen_names[s["name"]] = s["path"]
        # Description checks.
        if not s["description"]:
            issues.append({"severity": "error", "code": "missing-description",
                           "message": f"{label}: frontmatter has no 'description'. "
                                      "Agents use it to decide when to trigger the skill.",
                           "skill": s["name"]})
        else:
            d = s["description"]
            if len(d) < 20:
                issues.append({"severity": "warning", "code": "description-too-short",
                               "message": f"{label!r}: description is only {len(d)} chars. "
                                          "Say what it does AND when to use it.",
                               "skill": s["name"]})
            if len(d) > 1024:
                issues.append({"severity": "warning", "code": "description-too-long",
                               "message": f"{label!r}: description is {len(d)} chars (keep under 1024).",
                               "skill": s["name"]})
            if d in seen_descs:
                issues.append({"severity": "warning", "code": "duplicate-description",
                               "message": f"{label!r}: description is identical to {seen_descs[d]!r}. "
                                          "Two skills with the same trigger will fight each other.",
                               "skill": s["name"]})
            else:
                seen_descs[d] = s["name"] or label
        # Version hint (not required by the spec, but useful for packs).
        if not s["version"]:
            issues.append({"severity": "warning", "code": "no-version",
                           "message": f"{label}: no 'version' in frontmatter. "
                                      "Add one so users can tell whether they have the latest.",
                           "skill": s["name"]})

    # Pairwise overlap: skills whose descriptions are near-identical will
    # both trigger on the same prompts, so the agent picks arbitrarily.
    described = [s for s in skills if s["description"]]
    for i in range(len(described)):
        for j in range(i + 1, len(described)):
            a, b = described[i], described[j]
            sim = jaccard(tokens(a["description"]), tokens(b["description"]))
            if sim >= 0.7:
                issues.append({"severity": "warning", "code": "overlapping-description",
                               "message": f"{a['name']!r} and {b['name']!r}: descriptions are "
                                          f"{sim:.0%} similar. Merge them or make their triggers distinct.",
                               "skill": f"{a['name']} / {b['name']}"})

    errors = sum(1 for x in issues if x["severity"] == "error")
    warnings = sum(1 for x in issues if x["severity"] == "warning")
    return {
        "root": str(root),
        "skills": [{"name": s["name"], "path": s["path"], "description": s["description"],
                    "version": s["version"]} for s in skills],
        "skill_count": len(skills),
        "errors": errors,
        "warnings": warnings,
        "issues": sorted(issues, key=lambda x: (x["severity"] != "error", x["code"], str(x["skill"]))),
        "ok": errors == 0,
    }
