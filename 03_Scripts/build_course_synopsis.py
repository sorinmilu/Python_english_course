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
)

# ATX headings: hierarchy from ``#`` count only; leading outline numbers in titles are stripped.
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_CHAPTER_PREFIX_RE = re.compile(r"^CHAPTER\s*(?:\d+)?\s*:\s*", re.IGNORECASE)

CHAPTER_FILES = [
    "Chapter1_Synopsis.md",
    "Chapter2_Synopsis.md",
    "Chapter3_Synopsis.md",
    "Chapter4_Synopsis.md",
    "Chapter5_synopsis.md",
    "Chapter6_synopsis.md",
    "Chapter7_synopsis.md",
    "Chapter8_synopsis.md",
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


def _clean_heading_title(raw: str, *, heading_depth: int) -> str:
    """Normalize ATX title text; drop optional ``CHAPTER n:`` prefix on H1 lines."""
    t = _strip_heading_title_numbers(_clean_atx_title(raw))
    if heading_depth == 1:
        t = _CHAPTER_PREFIX_RE.sub("", t).strip() or t
    return t


def _infer_placeholder_chapter() -> dict[str, Any]:
    """When parsing needs a chapter root before any title is known (no H1/`# CHAPTER` yet)."""
    return make_outline_node(outline="1", title="Chapter")


def parse_chapter_file(path: Path) -> dict[str, Any] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    chapter: dict[str, Any] | None = None
    stack: list[dict[str, Any]] = []
    sibling_indices: list[int] = []

    def ensure_chapter() -> None:
        nonlocal chapter, stack, sibling_indices
        if chapter is None:
            chapter = _infer_placeholder_chapter()
            stack = [chapter]
            sibling_indices = []

    def next_synthetic_outline(depth: int) -> str:
        """Sibling-based placeholder outline (stripped before JSON export)."""
        while len(sibling_indices) < depth - 1:
            sibling_indices.append(0)
        while len(sibling_indices) > depth - 1:
            sibling_indices.pop()
        sibling_indices[-1] += 1
        return ".".join(["1", *[str(n) for n in sibling_indices]])

    def attach_by_heading_depth(node: dict[str, Any], depth: int) -> None:
        """Parent is the nearest stack node above this heading's ``#`` depth."""
        nonlocal stack, sibling_indices
        if depth <= 1:
            return
        while len(stack) >= depth:
            stack.pop()
        while len(sibling_indices) > depth - 1:
            sibling_indices.pop()
        if not stack:
            return
        stack[-1]["children"].append(node)
        stack.append(node)

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        match = ATX_HEADING_RE.match(line)
        if not match:
            continue

        hashes, title_raw = match.group(1), match.group(2)
        depth = len(hashes)
        title = _clean_heading_title(title_raw, heading_depth=depth)

        if depth == 1:
            chapter = make_outline_node(outline="1", title=title)
            stack = [chapter]
            sibling_indices = []
            continue

        ensure_chapter()
        node = make_outline_node(outline=next_synthetic_outline(depth), title=title)
        attach_by_heading_depth(node, depth)

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
