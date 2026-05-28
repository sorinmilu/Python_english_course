#!/usr/bin/env python3
"""Restore 00_CONTENT folders renamed with DELETED_ by sync (undo orphan rename).

Usage:
  conda activate python312 && python 03_Scripts/recover_deleted_content_folders.py \\
      --content-root /path/to/root_dir/00_CONTENT [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

DELETED_PREFIX = "DELETED_"


def recover(content_root: Path, *, dry_run: bool) -> list[str]:
    content_root = content_root.resolve()
    if not content_root.is_dir():
        raise SystemExit(f"Not a directory: {content_root}")

    actions: list[str] = []
    for child in sorted(content_root.iterdir()):
        if not child.is_dir() or not child.name.startswith(DELETED_PREFIX):
            continue
        original_name = child.name[len(DELETED_PREFIX) :]
        dest = content_root / original_name
        if dest.exists():
            actions.append(f"SKIP (target exists): {child.name} -> {original_name}")
            continue
        actions.append(f"RENAME: {child.name} -> {original_name}")
        if not dry_run:
            child.rename(dest)
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        required=True,
        help="Path to 00_CONTENT (e.g. under PhD Referat root_dir)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    actions = recover(args.content_root, dry_run=args.dry_run)
    if not actions:
        print("No DELETED_* directories found.")
        return
    for line in actions:
        print(line)
    if args.dry_run:
        print("\n(dry-run; no changes made)")


if __name__ == "__main__":
    main()
