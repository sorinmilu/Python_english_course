#!/usr/bin/env python3
"""Attach 'Possible output' verbatim blocks to program.json and remove them from content.tex."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROGRAM_TOKEN_RE = re.compile(r"%<<<PROGRAM:(programs/[^>]+)>>>")
OUTPUT_AFTER_PROGRAM_RE = re.compile(
    r"(%<<<PROGRAM:programs/[^>]+>>>)\s*"
    r"(?:Possible output(?:\s+excerpt|\s+on one CPython build)?\s*:)\s*"
    r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
    re.DOTALL | re.IGNORECASE,
)


def normalize_body(body: str) -> str:
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    return body


def fix_content_file(content_path: Path, apply: bool) -> list[dict]:
    text = content_path.read_text(encoding="utf-8")
    content_dir = content_path.parent
    fixes: list[dict] = []

    def replacer(match: re.Match[str]) -> str:
        token_line = match.group(1)
        output_body = normalize_body(match.group(2))
        program_rel = token_line.replace("%<<<PROGRAM:", "").replace(">>>", "").strip()
        program_dir = content_dir / program_rel
        json_path = program_dir / "program.json"
        if not json_path.is_file():
            fixes.append(
                {
                    "file": str(content_path.relative_to(REPO)),
                    "program": program_rel,
                    "status": "missing_program_json",
                }
            )
            return match.group(0)

        meta = json.loads(json_path.read_text(encoding="utf-8"))
        meta["output"] = output_body
        fixes.append(
            {
                "file": str(content_path.relative_to(REPO)),
                "program": program_rel,
                "status": "updated",
                "output_lines": len(output_body.splitlines()),
            }
        )
        if apply:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
                f.write("\n")
        return token_line + "\n"

    new_text, count = OUTPUT_AFTER_PROGRAM_RE.subn(replacer, text)
    if apply and count:
        content_path.write_text(new_text, encoding="utf-8")
    return fixes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(REPO))
    parser.add_argument("--content-dir", default="01_REDUCED_CONTENT")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    content_root = root / args.content_dir
    all_fixes: list[dict] = []

    for content_path in sorted(content_root.rglob("content.tex")):
        all_fixes.extend(fix_content_file(content_path, apply=args.apply))

    updated = [f for f in all_fixes if f.get("status") == "updated"]
    missing = [f for f in all_fixes if f.get("status") == "missing_program_json"]

    mode = "Applied" if args.apply else "Dry run"
    print(f"{mode}: {len(updated)} program outputs linked")
    if missing:
        print(f"Warning: {len(missing)} tokens without program.json")
    for item in updated:
        print(
            f"  + {item['program']} ({item['output_lines']} lines) "
            f"<- {item['file']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
