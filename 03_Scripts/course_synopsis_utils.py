"""Shared helpers for course_synopsis.json (build, validate, reorder, I/O)."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEADING_LEVELS = {
    "chapter": 1,
    "section": 2,
    "subsection": 3,
    "subsubsection": 4,
}

# Markdown outlines can temporarily exceed classic LaTeX's four heading tiers; cap at a
# sane bound so saves stay finite. (Export tools may still enforce shorter chains.)
MAX_HEADING_NUMBER_DEPTH = 12


def number_depth(number: str) -> int:
    return len(str(number).split("."))


def deepest_level_in_subtree(node: dict[str, Any]) -> int:
    """How many levels from this node down to the deepest descendant (this node counts as 1)."""
    children = node.get("children")
    if not isinstance(children, list) or not children:
        return 1
    return 1 + max(deepest_level_in_subtree(c) for c in children)


def validate_node_subtree(node: Any, *, max_depth: int) -> None:
    if not isinstance(node, dict):
        raise ValueError("each tree node must be an object")
    ch = node.get("children")
    if ch is None:
        raise ValueError("each node must have a children field")
    if not isinstance(ch, list):
        raise ValueError("children must be a list")
    for child in ch:
        validate_node_subtree(child, max_depth=max_depth)
    if deepest_level_in_subtree(node) > max_depth:
        raise ValueError(
            f"tree exceeds max outline depth ({max_depth} nesting levels)"
        )


def validate_tree(nodes: Any, *, max_depth: int = MAX_HEADING_NUMBER_DEPTH) -> None:
    """Reject malformed trees or nesting deeper than chapter→subsubsection."""
    if not isinstance(nodes, list):
        raise ValueError("tree must be a list")
    if len(nodes) == 0:
        raise ValueError("tree must not be empty")
    for node in nodes:
        validate_node_subtree(node, max_depth=max_depth)


def depth_to_type_level(depth: int) -> tuple[str, int]:
    """Map 1-based tree depth to synopsis type and heading level (capped at subsubsection)."""
    if depth <= 1:
        return "chapter", HEADING_LEVELS["chapter"]
    if depth == 2:
        return "section", HEADING_LEVELS["section"]
    if depth == 3:
        return "subsection", HEADING_LEVELS["subsection"]
    return "subsubsection", HEADING_LEVELS["subsubsection"]


def assign_preorder_ids_and_depth_types(nodes: list[dict[str, Any]]) -> None:
    """Stable sibling order: ids ``1..N`` preorder; type/level from depth; strip ``number`` / ``_outline``."""
    counter = 1

    def walk(ns: list[Any], depth: int) -> None:
        nonlocal counter
        if not isinstance(ns, list):
            return
        for node in ns:
            if not isinstance(node, dict):
                continue
            node["id"] = str(counter)
            counter += 1
            ntype, lvl = depth_to_type_level(depth)
            node["type"] = ntype
            node["level"] = lvl
            node.pop("number", None)
            node.pop("_outline", None)
            ch = node.get("children")
            if not isinstance(ch, list):
                node["children"] = []
            walk(node["children"], depth + 1)

    walk(nodes, 1)


def load_synopsis(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Course synopsis not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("course synopsis root must be a JSON object")
    tree = data.get("tree")
    if not isinstance(tree, list):
        raise ValueError("course synopsis must contain a tree array")
    return data


def save_synopsis(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with indent=2, UTF-8, trailing newline; replace atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def touch_meta_generated_at(data: dict[str, Any]) -> None:
    meta = data.get("meta")
    if not isinstance(meta, dict):
        data["meta"] = {}
        meta = data["meta"]
    meta["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def apply_reordered_tree(data: dict[str, Any], tree: list[dict[str, Any]]) -> dict[str, Any]:
    """Deep-copy synopsis, replace tree, validate, assign ids + depth types, update meta."""
    out = deepcopy(data)
    out["tree"] = deepcopy(tree)
    validate_tree(out["tree"])
    assign_preorder_ids_and_depth_types(out["tree"])
    out["schema_version"] = "2.0"
    touch_meta_generated_at(out)
    return out


def _one_line(text: str) -> str:
    return " ".join(text.splitlines()).strip()


def _node_id_plain(node: dict[str, Any]) -> str:
    return str(node.get("id") or "")


def _branch_expanded(node_id: str, expanded: dict[str, bool]) -> bool:
    if not node_id:
        return True
    return bool(expanded.get(node_id, True))


def _heading_markdown(node: dict[str, Any]) -> str:
    ntype = str(node.get("type") or "").lower()
    title = _one_line(str(node.get("title") or "(untitled)"))
    raw_level = node.get("level")
    if isinstance(raw_level, int):
        level = raw_level
    elif isinstance(raw_level, str) and raw_level.strip().isdigit():
        level = int(raw_level.strip())
    else:
        level = HEADING_LEVELS.get(ntype, 1)
    level = max(1, min(int(level), 6))
    hashes = "#" * level
    if ntype == "chapter":
        return f"# CHAPTER: {title}\n\n"
    return f"{hashes} {title}\n\n"


def _paragraphs_markdown(node: dict[str, Any]) -> str:
    raw = node.get("paragraphs")
    if not isinstance(raw, list) or not raw:
        return ""
    parts: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            chunk = (
                item.get("text")
                or item.get("body")
                or item.get("content")
                or item.get("markdown")
                or ""
            )
            t = str(chunk).strip()
        else:
            t = str(item).strip()
        if t:
            parts.append(t.rstrip())
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n\n"


def export_synopsis_tree_to_markdown(
    tree: list[dict[str, Any]],
    *,
    branch_expanded: dict[str, bool] | None = None,
) -> str:
    """Markdown export: only branches marked expanded in ``branch_expanded`` (default True).

    Headings use type/level only (``# CHAPTER:`` or ``##``…``####``); no outline or index numbers.

    Collapsed branches omit that node's heading, paragraphs, and all descendants.
    """
    exp = {str(k): bool(v) for k, v in (branch_expanded or {}).items()}
    chunks: list[str] = []

    def walk(nodes: Any) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            nid = _node_id_plain(node)
            if not _branch_expanded(nid, exp):
                continue
            chunks.append(_heading_markdown(node))
            chunks.append(_paragraphs_markdown(node))
            walk(node.get("children") or [])

    walk(tree)
    body = "".join(chunks).rstrip()
    return body + "\n" if body else "\n"


def save_text_file_atomic(path: Path, text: str) -> None:
    """Write UTF-8 text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text if text.endswith("\n") else text + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8", newline="\n")
    tmp.replace(path)
