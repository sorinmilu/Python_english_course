#!/usr/bin/env python3
"""Build course_synopsis.json from 99_Markdowns chapter outline files."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from course_synopsis_utils import (
    HEADING_LEVELS,
    assign_preorder_ids_and_depth_types,
    number_depth,
)

CHAPTER_HEADING_RE = re.compile(r"^#\s+CHAPTER\s+(\d+):\s*(.+)$", re.IGNORECASE)
# Real ATX headings: ## / ### / … with numbered title (e.g. ## 6.1 Title, #### 6.1.1.1 …)
ATX_NUMBERED_HEADING_RE = re.compile(
    r"^#{1,6}\s+(\d+(?:\.\d+)+)\s+(.+)$",
)
SUBSECTION_HEADING_RE = re.compile(r"^\*\s+\*\*(\d+(?:\.\d+)+)\s*(.+)\*\*")
BULLET_HEADING_RE = re.compile(r"^(\s+)\*\s+(\d+(?:\.\d+)+)\s+(.+)$")

CHAPTER_FILES = [
    "Chapter1_Synopsis.md",
    "Chapter2_Synopsis.md",
    "Chapter3_Synopsis.md",
    "Chapter4_Synopsis.md",
    "Chapter5_synopsis.md",
    "Chapter6_synopsis.md",
    "Chapter7_synopsis.md",
]

INTRODUCTION_CHAPTER = {
    "title": "Introduction",
    "paragraphs": [],
    "items": [],
    "metadata": {},
    "data": {},
    "children": [],
}


def shift_outline_first_segment(outline: str, offset: int) -> str:
    parts = outline.split(".")
    parts[0] = str(int(parts[0]) + offset)
    return ".".join(parts)


def shift_outline_tree(nodes: list[dict[str, Any]], chapter_offset: int) -> None:
    """Bump first segment of each node's temporary ``_outline`` (room for intro chapter)."""
    for node in nodes:
        ou = node.get("_outline")
        if isinstance(ou, str) and ou.strip():
            node["_outline"] = shift_outline_first_segment(ou, chapter_offset)
        shift_outline_tree(node.get("children") or [], chapter_offset)


_LEADING_OUTLINE_NUMBERS_RE = re.compile(r"^\d+(?:\.\d+)+\s+")


def _strip_heading_title_numbers(title: str) -> str:
    """Remove leading outline tokens like ``2.1.2.2.3 `` from heading text (outline is not stored in JSON)."""
    t = title.strip()
    while True:
        m = _LEADING_OUTLINE_NUMBERS_RE.match(t)
        if not m:
            break
        t = t[m.end() :].lstrip()
    out = t.strip()
    return out if out else title.strip()


def make_outline_node(*, outline: str, title: str) -> dict[str, Any]:
    cleaned = _strip_heading_title_numbers(title)
    return {
        "_outline": outline,
        "title": cleaned,
        "paragraphs": [],
        "items": [],
        "metadata": {},
        "data": {},
        "children": [],
    }


def _clean_atx_title(raw: str) -> str:
    """Strip closing ATX markers like ' ## ' at end of line."""
    t = raw.strip()
    t = re.sub(r"\s+#+\s*$", "", t)
    return t.strip()


def _infer_placeholder_chapter(path: Path) -> dict[str, Any]:
    """When a file has no '# CHAPTER …' line, root the outline at a synthetic chapter ``1``."""
    title_guess = path.stem.replace("_", " ").replace("-", " ")
    return make_outline_node(outline="1", title=title_guess or "Chapter")


def parse_chapter_file(path: Path) -> dict[str, Any] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    chapter: dict[str, Any] | None = None
    stack: list[dict[str, Any]] = []

    def ensure_chapter() -> None:
        nonlocal chapter, stack
        if chapter is None:
            chapter = _infer_placeholder_chapter(path)
            stack = [chapter]

    def attach_by_outline_depth(node: dict[str, Any]) -> None:
        """Parent is the nearest stack node with depth strictly less than this node's outline."""
        nonlocal stack
        ou = str(node.get("_outline") or "")
        d = number_depth(ou)
        if d <= 1:
            return
        while len(stack) >= d:
            stack.pop()
        if not stack:
            return
        stack[-1]["children"].append(node)
        stack.append(node)

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        match = CHAPTER_HEADING_RE.match(line)
        if match:
            number, title = match.group(1), match.group(2)
            chapter = make_outline_node(outline=number, title=title)
            stack = [chapter]
            continue

        match = ATX_NUMBERED_HEADING_RE.match(line)
        if match:
            ensure_chapter()
            num, title_raw = match.group(1), _clean_atx_title(match.group(2))
            node = make_outline_node(outline=num, title=title_raw)
            attach_by_outline_depth(node)
            continue

        match = SUBSECTION_HEADING_RE.match(line)
        if match:
            ensure_chapter()
            node = make_outline_node(outline=match.group(1), title=match.group(2))
            attach_by_outline_depth(node)
            continue

        match = BULLET_HEADING_RE.match(line)
        if match:
            ensure_chapter()
            node = make_outline_node(outline=match.group(2), title=match.group(3))
            attach_by_outline_depth(node)
            continue

    return chapter


def build_synopsis(repo_root: Path) -> dict[str, Any]:
    markdown_dir = repo_root / "99_Markdowns"
    tree: list[dict[str, Any]] = []

    for filename in CHAPTER_FILES:
        path = markdown_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing chapter markdown: {path}")
        chapter = parse_chapter_file(path)
        if chapter is not None:
            tree.append(chapter)

    shift_outline_tree(tree, chapter_offset=1)
    tree.insert(0, deepcopy(INTRODUCTION_CHAPTER))
    assign_preorder_ids_and_depth_types(tree)

    return {
        "schema_version": "2.0",
        "meta": {
            "title": "Python Course Synopsis",
            "description": (
                "Hierarchical course outline for tree display, drag-and-drop reorder, "
                "and Markdown/LaTeX export. Nodes use preorder-stable string ids "
                '"1".."N" only; headings in exported Markdown are unnumbered.'
            ),
            "source_dir": "99_Markdowns",
            "source_files": CHAPTER_FILES,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "latex_heading_levels": list(HEADING_LEVELS.keys()),
        },
        "tree": tree,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "00_CONTENT"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "course_synopsis.json"

    synopsis = build_synopsis(repo_root)
    output_path.write_text(
        json.dumps(synopsis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
