#!/usr/bin/env python3
"""Rename program sidecar directories to short names and update references."""

from __future__ import annotations

import json
import os
import re
import sys


from program_utils import section_prefix


def collect_program_dirs(content_root: str) -> list[tuple[str, str]]:
    """Return list of (programs_dir, content_tex_path)."""
    entries: list[tuple[str, str]] = []
    for dirpath, _dirnames, _filenames in os.walk(content_root):
        if os.path.basename(dirpath) != "programs":
            continue
        content_tex = os.path.join(os.path.dirname(dirpath), "content.tex")
        entries.append((dirpath, content_tex))
    return entries


def rename_programs_dir(programs_dir: str, content_tex: str) -> list[tuple[str, str]]:
    """Rename sidecars in one programs/ folder. Returns (old_slug, new_slug) pairs."""
    prefix = section_prefix(os.path.basename(os.path.dirname(programs_dir)))
    slugs = sorted(
        name
        for name in os.listdir(programs_dir)
        if os.path.isfile(os.path.join(programs_dir, name, "program.json"))
    )

    pairs: list[tuple[str, str]] = []
    for index, old_slug in enumerate(slugs, start=1):
        new_slug = f"{prefix}{index:02d}"
        if old_slug == new_slug:
            continue
        pairs.append((old_slug, new_slug))

    if not pairs:
        return []

    temp_paths: list[tuple[str, str]] = []
    for index, (old_slug, new_slug) in enumerate(pairs):
        old_path = os.path.join(programs_dir, old_slug)
        temp_path = os.path.join(programs_dir, f"__renaming_{index:03d}__")
        os.rename(old_path, temp_path)
        temp_paths.append((temp_path, os.path.join(programs_dir, new_slug), new_slug))

    for temp_path, new_path, new_slug in temp_paths:
        os.rename(temp_path, new_path)
        json_path = os.path.join(new_path, "program.json")
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["label"] = new_slug
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if os.path.isfile(content_tex):
        with open(content_tex, "r", encoding="utf-8") as f:
            content = f.read()
        updated = content
        for old_slug, new_slug in sorted(pairs, key=lambda item: len(item[0]), reverse=True):
            updated = updated.replace(
                f"%<<<PROGRAM:programs/{old_slug}",
                f"%<<<PROGRAM:programs/{new_slug}",
            )
        if updated != content:
            with open(content_tex, "w", encoding="utf-8") as f:
                f.write(updated)

    return pairs


def main() -> int:
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "..")
    content_root = os.path.join(root, "00_CONTENT")
    program_dirs = collect_program_dirs(content_root)

    total = 0
    for programs_dir, content_tex in program_dirs:
        pairs = rename_programs_dir(programs_dir, content_tex)
        if pairs:
            rel = os.path.relpath(programs_dir, root).replace("\\", "/")
            print(f"{rel}:")
            for old_slug, new_slug in pairs:
                print(f"  programs/{old_slug} -> programs/{new_slug}")
            total += len(pairs)

    print(f"Renamed {total} sidecars.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
