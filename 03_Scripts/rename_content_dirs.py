#!/usr/bin/env python3
"""Shorten long 00_CONTENT directory names and refresh main_project.json paths."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

MAX_DIR_NAME_LEN = 28
MAX_BODY_LEN = 22
INDEXED_DIR_RE = re.compile(r"^(\d{2})_(.+)$")
HASH_SUFFIX_RE = re.compile(r"_[0-9a-f]{8}$")


def split_words(body: str) -> list[str]:
    if "_" in body:
        parts = [p for p in body.split("_") if p]
        if parts:
            return parts
    return re.findall(r"[A-Z]?[a-z0-9]+", body) or [body]


def shorten_dir_name(name: str) -> str | None:
    if name in {"programs", "diagrams"}:
        return None
    if len(name) <= MAX_DIR_NAME_LEN:
        return None

    match = INDEXED_DIR_RE.match(name)
    if not match:
        return name[:MAX_DIR_NAME_LEN].rstrip("_")

    idx, body = match.group(1), match.group(2)
    body = HASH_SUFFIX_RE.sub("", body)
    words = split_words(body)

    chunks: list[str] = []
    for word in words:
        token = word.lower()[:8]
        if token and (not chunks or token != chunks[-1]):
            chunks.append(token)
        if len("_".join(chunks)) >= MAX_BODY_LEN:
            break

    short_body = "_".join(chunks)[:MAX_BODY_LEN].rstrip("_") or body[:MAX_BODY_LEN].lower()
    return f"{idx}_{short_body}"


def collect_dirs(content_root: Path) -> list[Path]:
    dirs: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(content_root):
        current = Path(dirpath)
        if current == content_root:
            continue
        dirs.append(current)
    return sorted(dirs, key=lambda p: len(p.parts), reverse=True)


def unique_name(parent: Path, desired: str, old_name: str) -> str:
    if desired == old_name:
        return desired
    candidate = desired
    counter = 2
    while (parent / candidate).exists() and candidate != old_name:
        suffix = f"_{counter:02d}"
        base = desired[: max(1, MAX_DIR_NAME_LEN - len(suffix))].rstrip("_")
        candidate = f"{base}{suffix}"
        counter += 1
    return candidate


def rename_directories(content_root: Path) -> dict[str, str]:
    """Return mapping old relative path -> new relative path (from content_root)."""
    mapping: dict[str, str] = {}
    for directory in collect_dirs(content_root):
        old_name = directory.name
        new_name = shorten_dir_name(old_name)
        if not new_name or new_name == old_name:
            continue
        new_name = unique_name(directory.parent, new_name, old_name)
        if new_name == old_name:
            continue

        old_rel = directory.relative_to(content_root).as_posix()
        temp_path = directory.parent / f"__renaming__{old_name}"
        directory.rename(temp_path)
        final_path = directory.parent / new_name
        temp_path.rename(final_path)
        new_rel = final_path.relative_to(content_root).as_posix()
        mapping[old_rel] = new_rel
        print(f"  {old_rel} -> {new_rel}")

    return mapping


def apply_mapping_to_text(text: str, mapping: dict[str, str]) -> str:
    updated = text
    for old_rel, new_rel in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        updated = updated.replace(old_rel, new_rel)
    return updated


def collect_inspected_folders(content_root: Path, root_dir: Path) -> list[str]:
    prefix = content_root.relative_to(root_dir).as_posix()
    folders: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(content_root):
        if "content.tex" not in filenames:
            continue
        rel = Path(dirpath).relative_to(root_dir).as_posix().rstrip("/") + "/"
        folders.append(rel)
    folders.sort()
    return folders


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "..").resolve()
    content_root = root / "00_CONTENT"
    config_path = root / "03_Scripts" / "main_project.json"

    if not content_root.is_dir():
        print(f"Missing content root: {content_root}")
        return 1

    print("Renaming long directories under 00_CONTENT...")
    mapping = rename_directories(content_root)
    print(f"Renamed {len(mapping)} directories.")

    if config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        old_folders = config.get("inspected_folders", [])
        new_folders = collect_inspected_folders(content_root, root)
        config["inspected_folders"] = new_folders

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")

        changed = sum(1 for a, b in zip(old_folders, new_folders) if a != b)
        print(f"Updated main_project.json inspected_folders ({len(new_folders)} entries, {changed} path changes).")
    else:
        print(f"Warning: config not found at {config_path}")

    report_path = root / "build" / "temp" / "dir_rename_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"renamed": mapping}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Report: {report_path.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
