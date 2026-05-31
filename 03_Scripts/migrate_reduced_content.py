#!/usr/bin/env python3
"""Helpers for 00_CONTENT -> 01_REDUCED_CONTENT migration."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "00_CONTENT"
DST = REPO / "01_REDUCED_CONTENT"

# Folders to omit entirely (relative to 00_CONTENT/)
OMIT_FOLDERS = {
    "02_intro_to_python/00_historic_context_and_d/02_why_python_spread_scri",
    "03_variables/00_identifi_and_syntax_ru/01_stylisti_coding_conven",
    "03_variables/02_singular_data_domains/02_the_complex_represen_a",
}

SECTION_DELETE_TITLES = [
    # chapter 4 cross-chapter
    "The Evolution of Multitasking Subsystems: Time-Slicing Hardware Resources",
    "Valid Characters: Letters, Digits, Underscore (_), and Unicode Identifier Rules",
    "Stylistic Coding Conventions",
    "Alignment with the PEP 8 Style Guide",
    "Readable Naming Conventions: Lowercase snake_case for Ordinary Variables",
    "Octal Literal Parsing Boundaries",
    "Formal Lexical Extraction: Querying Literals via System Naming Maps",
    "Planar Transformations: 16-Bit Base-16 Codepoint Escapes via",
    "Absolute Space Mapping: 32-Bit Base-16 Extended Codepoint Escapes via",
    # chapter 5 sequential
    "Indexing: Zero-Based Component Addressing",
    "Length, Membership, and Iteration:",
    "Concatenation and Repetition:",
    "Equality and Lexicographic Comparison Rules",
    "Searching and Membership:",
    "Replacement and Case Transformation:",
    "Appending and Extending:",
    "Removing Elements:",
    "Sorting and Reversing In Place:",
    "Tuple Packing: Comma-Based Construction",
    # chapter 6 control flow
    "Sequential Evaluation: The Structure of",
    "Indefinite Iteration: Guard Conditions",
    "Definite Iteration: Foundations of the",
    "Loop Interruptions: The Syntax of",
    "Basic Exception Trapping:",
    # chapter 7 hash
    "Sequential Collections: Why Lists, Tuples, and Strings Locate",
    "Building Dictionaries from Pair Sequences",
    "Modifying Mappings: Adding, Updating, and Removing",
    "Accessor Methods: Querying Keys, Values, and Items",
    "Set Architectures: Syntax and Mathematical Operations",
    # chapter 8 functions
    "Basic Function Declarations:",
    "Function Documentation: Docstrings",
    "Parameter Mappings: Positional and Named",
    "The Return Statement: Terminating Execution",
    # chapter 9 io
    "Basic File Access: Opening and Closing",
    "Text Input Operations: Processing Files",
    "Text Output Mechanics: Exporting Buffers",
    "Legacy Path Manipulations: Navigating Directories",
    "Tabular Data Processing: Basic Layout Ingest",
]


def _title_matches(line: str, titles: list[str]) -> bool:
    if not re.search(r"\\(chapter|section|subsection|subsubsection)\{", line):
        return False
    for t in titles:
        if t in line:
            return True
    return False


def strip_sections(tex: str, titles: list[str] | None = None) -> str:
    titles = titles or SECTION_DELETE_TITLES
    lines = tex.splitlines(keepends=True)
    out: list[str] = []
    skip_depth: int | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"\\(chapter|section|subsection|subsubsection)\{", line)
        if m:
            level = {"chapter": 0, "section": 1, "subsection": 2, "subsubsection": 3}[m.group(1)]
            if _title_matches(line, titles):
                skip_depth = level
                i += 1
                continue
            if skip_depth is not None and level <= skip_depth:
                skip_depth = None
        if skip_depth is None:
            out.append(line)
        i += 1
    return "".join(out)


def copy_chapter(chapter_dir: str, omit: set[str] | None = None) -> None:
    omit = omit or OMIT_FOLDERS
    src_root = SRC / chapter_dir
    dst_root = DST / chapter_dir
    if dst_root.exists():
        shutil.rmtree(dst_root)
    for path in src_root.rglob("*"):
        rel = path.relative_to(src_root)
        rel_s = rel.as_posix()
        if any(rel_s == o or rel_s.startswith(o + "/") for o in omit):
            continue
        target = dst_root / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".tex":
                text = path.read_text(encoding="utf-8")
                shutil.copy2(path, target)
            else:
                shutil.copy2(path, target)


def collect_inspected_folders() -> list[str]:
    folders: list[str] = []
    for d in sorted(DST.rglob("*")):
        if d.is_dir() and ((d / "content.tex").exists() or any(d.iterdir())):
            rel = d.relative_to(REPO).as_posix() + "/"
            if rel not in folders:
                folders.append(rel)
    # Only dirs that are ancestors of content.tex or listed in main project style
    content_dirs = {p.parent.relative_to(REPO).as_posix() + "/" for p in DST.rglob("content.tex")}
    all_dirs: set[str] = set()
    for cd in content_dirs:
        parts = Path(cd.rstrip("/")).parts
        for i in range(1, len(parts) + 1):
            all_dirs.add("/".join(parts[:i]) + "/")
    return sorted(all_dirs)


def write_reduced_project_json() -> None:
    main = json.loads((REPO / "03_Scripts" / "main_project.json").read_text(encoding="utf-8"))
    omit_paths = {f"00_CONTENT/{o}" for o in OMIT_FOLDERS}
    disk = set(collect_inspected_folders())
    folders = sorted(
        p.replace("00_CONTENT/", "01_REDUCED_CONTENT/")
        for p in main["inspected_folders"]
        if p not in omit_paths and p.replace("00_CONTENT/", "01_REDUCED_CONTENT/") in disk
    )
    # Add leaf dirs created by migration but absent from main (e.g. pickle section)
    main_reduced = {p.replace("00_CONTENT/", "01_REDUCED_CONTENT/") for p in main["inspected_folders"]}
    for d in sorted(disk):
        if d not in folders and not any(d.startswith(m) for m in main_reduced if m != d):
            parent = "/".join(d.rstrip("/").split("/")[:-1]) + "/"
            if parent.replace("01_REDUCED_CONTENT/", "") and parent in disk:
                folders.append(d)
    folders = sorted(set(folders))
    folders = [f for f in folders if f != "01_REDUCED_CONTENT/"]
    main["initial_project_structure"]["relative_path"] = "../01_REDUCED_CONTENT"
    main["inspected_folders"] = folders
    out = REPO / "03_Scripts" / "reduced_project.json"
    out.write_text(json.dumps(main, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(folders)} folders)")


def apply_section_strips_under(dst_rel: str) -> None:
    root = DST / dst_rel
    for tex in root.rglob("content.tex"):
        original = tex.read_text(encoding="utf-8")
        stripped = strip_sections(original)
        if stripped != original:
            tex.write_text(stripped, encoding="utf-8")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--write-json", action="store_true")
    ap.add_argument("--strip-sections", metavar="CHAPTER_DIR")
    args = ap.parse_args()
    if args.strip_sections:
        apply_section_strips_under(args.strip_sections)
    if args.write_json:
        write_reduced_project_json()
