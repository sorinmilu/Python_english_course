"""Sync course synopsis tree to LaTeX folder layout under root_dir's 00_CONTENT."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from course_synopsis_utils import save_text_file_atomic

MAX_SLUG_LEN = 80
INDEXED_DIR_RE = re.compile(r"^\d{2}_")
DELETED_PREFIX = "DELETED_"


def slug_snake(title: str, *, max_len: int = MAX_SLUG_LEN) -> str:
    """Lowercase slug with underscores."""
    words = re.findall(r"[A-Za-z0-9]+", str(title))
    if not words:
        base = "untitled"
    else:
        base = "_".join(w.lower() for w in words)
    return _truncate_slug(base, max_len)


def slug_camel(title: str, *, max_len: int = MAX_SLUG_LEN) -> str:
    """lowerCamelCase slug from title words."""
    words = re.findall(r"[A-Za-z0-9]+", str(title))
    if not words:
        base = "untitled"
    else:
        first = words[0].lower()
        rest = "".join(w[:1].upper() + w[1:].lower() for w in words[1:])
        base = first + rest
    return _truncate_slug(base, max_len)


def _truncate_slug(base: str, max_len: int) -> str:
    if len(base) <= max_len:
        return base
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:8]
    keep = max(1, max_len - 9)
    trimmed = base[:keep].rstrip("_")
    return f"{trimmed}_{digest}"


def indexed_dir_name(index: int, slug: str) -> str:
    return f"{index:02d}_{slug}"


def latex_heading(command: str, title: str) -> str:
    return f"\\{command}{{{title}}}\n"


def build_subsection_content_tex(subsection_title: str, subsubsections: list[str]) -> str:
    parts = [latex_heading("subsection", subsection_title)]
    for sub_title in subsubsections:
        parts.append(latex_heading("subsubsection", sub_title))
    return "".join(parts)


@dataclass
class ExpectedFolder:
    """One synced directory (chapter, section, or subsection)."""

    abs_path: Path
    rel_to_root: str
    content_tex: str | None = None


@dataclass
class SyncResult:
    created_dirs: int = 0
    skipped_dirs: int = 0
    created_files: int = 0
    skipped_files: int = 0
    renamed_orphans: list[str] = field(default_factory=list)
    pending_orphans: list[str] = field(default_factory=list)
    inspected_folders: list[str] = field(default_factory=list)
    dry_run: bool = False


def build_expected_layout(
    tree: list[dict[str, Any]],
    *,
    content_root: Path,
    root_dir: Path,
) -> list[ExpectedFolder]:
    """Preorder list of expected folders with content.tex payloads."""
    content_root = content_root.resolve()
    root_dir = root_dir.resolve()
    try:
        content_rel_prefix = content_root.relative_to(root_dir).as_posix()
    except ValueError:
        content_rel_prefix = content_root.name

    out: list[ExpectedFolder] = []

    def rel_folder(*parts: str) -> str:
        frag = "/".join(p for p in (content_rel_prefix, *parts) if p)
        return frag.rstrip("/") + "/"

    for ch_i, chapter in enumerate(tree):
        if not isinstance(chapter, dict):
            continue
        ch_title = str(chapter.get("title") or "Untitled")
        ch_slug = slug_snake(ch_title)
        ch_dir_name = indexed_dir_name(ch_i, ch_slug)
        ch_path = _resolve_existing_dir(content_root, ch_dir_name)
        out.append(
            ExpectedFolder(
                abs_path=ch_path,
                rel_to_root=rel_folder(ch_dir_name),
                content_tex=latex_heading("chapter", ch_title),
            )
        )
        sections = chapter.get("children") or []
        if not isinstance(sections, list):
            continue
        for sec_i, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            sec_title = str(section.get("title") or "Untitled")
            sec_slug = slug_snake(sec_title)
            sec_dir_name = indexed_dir_name(sec_i, sec_slug)
            sec_path = ch_path / sec_dir_name
            out.append(
                ExpectedFolder(
                    abs_path=sec_path,
                    rel_to_root=rel_folder(ch_dir_name, sec_dir_name),
                    content_tex=latex_heading("section", sec_title),
                )
            )
            subsections = section.get("children") or []
            if not isinstance(subsections, list):
                continue
            for sub_i, subsection in enumerate(subsections):
                if not isinstance(subsection, dict):
                    continue
                sub_title = str(subsection.get("title") or "Untitled")
                sub_slug = slug_camel(sub_title)
                sub_dir_name = indexed_dir_name(sub_i, sub_slug)
                sub_path = sec_path / sub_dir_name
                subsubs = subsection.get("children") or []
                subsub_titles: list[str] = []
                if isinstance(subsubs, list):
                    for subsub in subsubs:
                        if isinstance(subsub, dict):
                            subsub_titles.append(str(subsub.get("title") or "Untitled"))
                out.append(
                    ExpectedFolder(
                        abs_path=sub_path,
                        rel_to_root=rel_folder(ch_dir_name, sec_dir_name, sub_dir_name),
                        content_tex=build_subsection_content_tex(sub_title, subsub_titles),
                    )
                )

    return out


def _ensure_empty_file(path: Path, *, created: int, skipped: int) -> tuple[int, int]:
    if path.is_file():
        return created, skipped + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8", newline="\n")
    return created + 1, skipped


def _ensure_content_tex(path: Path, text: str, *, created: int, skipped: int) -> tuple[int, int]:
    if path.is_file():
        return created, skipped + 1
    save_text_file_atomic(path, text.rstrip("\n"))
    return created + 1, skipped


def _collect_orphans(parent: Path, expected_names: set[str]) -> list[Path]:
    if not parent.is_dir():
        return []
    orphans: list[Path] = []
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(DELETED_PREFIX):
            continue
        if not INDEXED_DIR_RE.match(name):
            continue
        if name not in expected_names:
            orphans.append(child)
    return orphans


def _actual_dir_name(parent: Path, expected_name: str) -> str | None:
    """Return the on-disk directory name matching expected_name (index + slug), if any."""
    if not parent.is_dir() or len(expected_name) < 4 or expected_name[2] != "_":
        return None
    prefix = expected_name[:3]
    needle = expected_name[3:].casefold()
    for child in parent.iterdir():
        if not child.is_dir() or child.name.startswith(DELETED_PREFIX):
            continue
        if (
            len(child.name) > 3
            and child.name[:3] == prefix
            and child.name[3:].casefold() == needle
        ):
            return child.name
    return None


def _resolve_existing_dir(parent: Path, expected_name: str) -> Path:
    """Use existing sibling; prefer real on-disk spelling (e.g. 00_Introduction)."""
    actual = _actual_dir_name(parent, expected_name)
    if actual is not None:
        return parent / actual
    return parent / expected_name


def folder_rel_to_root(folder_path: Path, root_dir: Path) -> str:
    """Path relative to root_dir with trailing slash (for inspected_folders)."""
    rel = folder_path.resolve().relative_to(root_dir.resolve()).as_posix()
    return rel.rstrip("/") + "/"


def _resolve_expected_folders(
    expected: list[ExpectedFolder],
    *,
    root_dir: Path,
) -> list[ExpectedFolder]:
    """Map each expected folder to an on-disk path (case-insensitive match)."""
    root_dir = root_dir.resolve()
    resolved: list[ExpectedFolder] = []
    for folder in expected:
        path = _resolve_existing_dir(folder.abs_path.parent, folder.abs_path.name)
        resolved.append(
            ExpectedFolder(
                abs_path=path,
                rel_to_root=folder_rel_to_root(path, root_dir),
                content_tex=folder.content_tex,
            )
        )
    return resolved


def _rename_orphan(path: Path) -> Path:
    dest = path.parent / f"{DELETED_PREFIX}{path.name}"
    if dest.exists():
        suffix = 1
        while dest.exists():
            dest = path.parent / f"{DELETED_PREFIX}{path.name}_{suffix}"
            suffix += 1
    path.rename(dest)
    return dest


def collect_pending_orphans(
    expected: list[ExpectedFolder],
    *,
    content_root: Path,
) -> list[str]:
    """List orphan indexed dirs (relative to content_root) that would be DELETED_-prefixed."""
    content_root = content_root.resolve()
    expected_by_parent: dict[Path, set[str]] = {}
    for folder in expected:
        parent = folder.abs_path.parent
        expected_by_parent.setdefault(parent, set()).add(folder.abs_path.name)

    pending: list[str] = []
    for parent, names in expected_by_parent.items():
        for orphan in _collect_orphans(parent, names):
            pending.append(str(orphan.relative_to(content_root)))
    return pending


def sync_content_tree(
    tree: list[dict[str, Any]],
    *,
    content_root: Path,
    root_dir: Path,
    rename_orphans: bool = False,
    dry_run: bool = False,
) -> SyncResult:
    """Create missing folders/files; optionally rename orphan indexed directories."""
    content_root = content_root.resolve()
    root_dir = root_dir.resolve()
    expected = _resolve_expected_folders(
        build_expected_layout(tree, content_root=content_root, root_dir=root_dir),
        root_dir=root_dir,
    )
    result = SyncResult(dry_run=dry_run)
    result.pending_orphans = collect_pending_orphans(expected, content_root=content_root)

    if rename_orphans and not dry_run:
        expected_by_parent: dict[Path, set[str]] = {}
        for folder in expected:
            parent = folder.abs_path.parent
            expected_by_parent.setdefault(parent, set()).add(folder.abs_path.name)

        for parent, names in expected_by_parent.items():
            for orphan in _collect_orphans(parent, names):
                new_path = _rename_orphan(orphan)
                result.renamed_orphans.append(str(new_path.relative_to(content_root)))

    if dry_run:
        result.inspected_folders = [f.rel_to_root for f in expected]
        return result

    for folder in expected:
        resolved_path = folder.abs_path
        result.inspected_folders.append(folder.rel_to_root)
        if resolved_path.is_dir():
            result.skipped_dirs += 1
        else:
            resolved_path.mkdir(parents=True, exist_ok=True)
            result.created_dirs += 1

        bib = resolved_path / "references.bib"
        c, s = _ensure_empty_file(bib, created=result.created_files, skipped=result.skipped_files)
        result.created_files, result.skipped_files = c, s

        if folder.content_tex is not None:
            tex = resolved_path / "content.tex"
            c, s = _ensure_content_tex(
                tex,
                folder.content_tex,
                created=result.created_files,
                skipped=result.skipped_files,
            )
            result.created_files, result.skipped_files = c, s

    return result
