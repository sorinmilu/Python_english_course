#!/usr/bin/env python3
"""Fix program.json titles using balanced-brace heading extraction."""

from __future__ import annotations

import json
import os
import re
import sys

from program_utils import clean_latex_heading, extract_last_heading_title

PROGRAM_TOKEN_RE = re.compile(r"%<<<PROGRAM:(.+?)>>>")


def fix_titles_in_file(content_path: str) -> int:
    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    content_dir = os.path.dirname(content_path)
    updated = 0

    for match in PROGRAM_TOKEN_RE.finditer(content):
        program_rel = match.group(1).split("|", 1)[0].strip()
        program_dir = os.path.join(content_dir, program_rel)
        json_path = os.path.join(program_dir, "program.json")
        if not os.path.isfile(json_path):
            continue

        prose_before = content[: match.start()]
        heading = extract_last_heading_title(prose_before)
        if not heading:
            continue

        title = clean_latex_heading(heading.strip())
        if len(title) > 80:
            title = title[:77].rstrip() + "..."

        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if meta.get("title") == title:
            continue

        meta["title"] = title
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")
        updated += 1

    return updated


def main() -> int:
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "..")
    content_root = os.path.join(root, "00_CONTENT")
    total = 0

    for dirpath, _dirnames, filenames in os.walk(content_root):
        if "content.tex" not in filenames:
            continue
        total += fix_titles_in_file(os.path.join(dirpath, "content.tex"))

    print(f"Updated {total} program titles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
