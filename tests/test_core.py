"""Tests for skill-audit. Run with: python -m pytest -q"""

import json
import subprocess
import sys
from pathlib import Path

from skill_audit.core import audit, jaccard, parse_frontmatter, tokens


def write_skill(root: Path, dirname: str, frontmatter: str, body: str = "Do the thing. Step 1. Step 2. More instructions here to pass the thin-body check."):
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n{body}\n")
    return d


def test_frontmatter_basic():
    fields, body, warns = parse_frontmatter("---\nname: foo\ndescription: Does foo.\n---\n\nBody here.\n")
    assert fields == {"name": "foo", "description": "Does foo."}
    assert "Body here" in body
    assert warns == []


def test_frontmatter_missing():
    fields, _, warns = parse_frontmatter("No frontmatter here.\n")
    assert fields == {}
    assert warns


def test_frontmatter_with_bom():
    # Files saved with a UTF-8 BOM (common from Windows editors) must still parse.
    fields, _, warns = parse_frontmatter("﻿---\nname: foo\ndescription: Does foo when needed.\n---\n\nBody here.\n")
    assert fields["name"] == "foo"
    assert warns == []


def test_frontmatter_leading_blank_lines():
    # A blank first line (or leading spaces) must not hide the frontmatter.
    fields, _, warns = parse_frontmatter("\n\n---\nname: foo\ndescription: Does foo when needed.\n---\n\nBody here.\n")
    assert fields["name"] == "foo"
    assert warns == []
    fields, _, warns = parse_frontmatter("  \n---\nname: foo\ndescription: Does foo when needed.\n---\n\nBody here.\n")
    assert fields["name"] == "foo"
    assert warns == []


def test_tokens_and_jaccard():
    assert jaccard(tokens("review pull requests for bugs"), tokens("review pull requests for bugs")) == 1.0
    assert jaccard(tokens("alpha beta gamma"), tokens("delta epsilon zeta")) == 0.0


def test_good_pack_passes(tmp_path: Path):
    write_skill(tmp_path, "code-review", 'name: code-review\ndescription: Review a pull request for bugs, security issues and missing tests.\nversion: "1.0.0"')
    write_skill(tmp_path, "git-helper", 'name: git-helper\ndescription: Help with git branches, rebasing and resolving merge conflicts safely.\nversion: "1.0.0"')
    result = audit(tmp_path)
    assert result["ok"] is True
    assert result["skill_count"] == 2


def test_duplicate_name_is_error(tmp_path: Path):
    write_skill(tmp_path, "a", 'name: dup\ndescription: First skill that does review work thoroughly.\nversion: "1.0.0"')
    write_skill(tmp_path, "b", 'name: dup\ndescription: Second skill that writes documentation clearly.\nversion: "1.0.0"')
    result = audit(tmp_path)
    assert not result["ok"]
    assert any(i["code"] == "duplicate-name" for i in result["issues"])


def test_invalid_name_and_missing_description(tmp_path: Path):
    write_skill(tmp_path, "bad", 'name: "Bad Name"\nversion: "1.0.0"')
    result = audit(tmp_path)
    codes = {i["code"] for i in result["issues"]}
    assert "invalid-name" in codes
    assert "missing-description" in codes


def test_overlapping_descriptions_warn(tmp_path: Path):
    write_skill(tmp_path, "a", 'name: review-a\ndescription: Review pull requests for bugs, security issues and missing tests.\nversion: "1.0.0"')
    write_skill(tmp_path, "b", 'name: review-b\ndescription: Review pull requests for bugs, security issues and missing tests carefully.\nversion: "1.0.0"')
    result = audit(tmp_path)
    assert any(i["code"] == "overlapping-description" for i in result["issues"])


def test_cli_json_and_list(tmp_path: Path):
    write_skill(tmp_path, "code-review", 'name: code-review\ndescription: Review a pull request for bugs, security issues and missing tests.\nversion: "1.0.0"')
    repo_src = str(Path(__file__).resolve().parents[1] / "src")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "PYTHONPATH": repo_src, "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run(
        [sys.executable, "-m", "skill_audit", "check", "--path", str(tmp_path), "--format", "json"],
        capture_output=True, text=True, check=True, env=env,
    )
    data = json.loads(out.stdout)
    assert data["ok"] is True
    out2 = subprocess.run(
        [sys.executable, "-m", "skill_audit", "list", "--path", str(tmp_path)],
        capture_output=True, text=True, check=True, env=env,
    )
    assert "code-review" in out2.stdout
