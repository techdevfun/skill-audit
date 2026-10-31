"""Command line interface for skill-audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import audit


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skill-audit",
        description="Audit Agent Skills packs: duplicates, conflicts, missing metadata.",
    )
    p.add_argument("--version", action="version", version="skill-audit 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Audit a skills directory.")
    check.add_argument("--path", default=".", help="Root dir containing skill folders (default: .)")
    check.add_argument("--format", choices=["text", "json"], default="text")
    check.add_argument("--quiet", action="store_true", help="Only print the summary line.")

    lst = sub.add_parser("list", help="List discovered skills.")
    lst.add_argument("--path", default=".", help="Root dir containing skill folders (default: .)")
    lst.add_argument("--format", choices=["text", "json"], default="text")
    return p


def format_text(result: dict) -> str:
    lines: list[str] = []
    if not result["issues"]:
        lines.append(f"OK: {result['skill_count']} skill(s) look clean.")
        return "\n".join(lines)
    for it in result["issues"]:
        mark = "ERROR" if it["severity"] == "error" else "WARN "
        lines.append(f"[{mark}] {it['code']}: {it['message']}")
    lines.append(f"Summary: {result['errors']} error(s), {result['warnings']} warning(s), "
                 f"{result['skill_count']} skill(s).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.path)
    result = audit(root)
    if args.command == "check":
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.quiet:
            print(f"{result['errors']} error(s), {result['warnings']} warning(s), "
                  f"{result['skill_count']} skill(s).")
        else:
            print(format_text(result))
        return 0 if result["ok"] else 1
    if args.command == "list":
        dir_error = next((it for it in result["issues"] if it["code"] == "missing-dir"), None)
        if dir_error is not None:
            # A wrong --path should fail loudly, not pretend the pack is empty.
            print(f"Error: {dir_error['message']}", file=sys.stderr)
            return 1
        if args.format == "json":
            print(json.dumps(result["skills"], indent=2))
        else:
            if not result["skills"]:
                print("No skills found.")
            for s in result["skills"]:
                desc = (s["description"] or "(no description)")[:90]
                print(f"- {s['name'] or '(unnamed)'}: {desc}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
