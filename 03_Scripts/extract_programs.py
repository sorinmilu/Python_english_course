#!/usr/bin/env python3
"""One-time migration: extract high-confidence verbatim code blocks into program sidecars."""

from __future__ import annotations

import argparse
import json
import os
import sys

from program_utils import (
    detect_output_pair,
    find_verbatim_blocks,
    infer_title,
    is_extractable_program,
    make_slug,
    section_prefix,
    write_program_sidecar,
)


def find_content_files(root_dir: str) -> list[str]:
    content_root = os.path.join(root_dir, "00_CONTENT")
    paths = []
    for dirpath, _dirnames, filenames in os.walk(content_root):
        if "content.tex" in filenames:
            paths.append(os.path.join(dirpath, "content.tex"))
    return sorted(paths)


def extract_from_file(content_path: str, root_dir: str, apply: bool) -> dict:
    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    content_dir = os.path.dirname(content_path)
    rel_content = os.path.relpath(content_path, root_dir).replace("\\", "/")

    accepted = []
    rejected = []
    used_slugs: set[str] = set()
    slug_prefix = section_prefix(os.path.basename(content_dir))

    blocks = find_verbatim_blocks(content)
    # Process from end to start so string offsets stay valid during replacement.
    replacements: list[tuple[int, int, str]] = []

    for block in reversed(blocks):
        body = block["body"]
        ok, reason, lang = is_extractable_program(body)
        if not ok:
            rejected.append(
                {
                    "file": rel_content,
                    "reason": reason,
                    "preview": body.splitlines()[0][:80] if body else "",
                }
            )
            continue

        output_text, out_start, out_end = detect_output_pair(content, block["end"])
        prose_before = content[: block["start"]]
        title = infer_title(prose_before, body, lang or "text")
        slug = make_slug(title, lang or "text", used_slugs, prefix=slug_prefix)

        program_rel = f"programs/{slug}"
        program_dir = os.path.join(content_dir, program_rel)

        meta = {
            "language": lang,
            "title": title,
            "label": slug,
            "linenos": True,
            "input": None,
            "output": output_text,
        }

        accepted.append(
            {
                "file": rel_content,
                "slug": slug,
                "language": lang,
                "title": title,
                "program_dir": program_rel.replace("\\", "/"),
                "has_output": output_text is not None,
            }
        )

        replace_start = block["start"]
        replace_end = out_end if output_text is not None else block["end"]
        placeholder = f"%<<<PROGRAM:{program_rel.replace(chr(92), '/')}>>>"
        replacements.append((replace_start, replace_end, placeholder))

        if apply:
            write_program_sidecar(program_dir, meta, body)

    if apply and replacements:
        new_content = content
        for start, end, placeholder in sorted(replacements, key=lambda item: item[0], reverse=True):
            new_content = (
                new_content[:start]
                + placeholder
                + "\n"
                + new_content[end:].lstrip("\n")
            )
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return {
        "file": rel_content,
        "accepted": accepted,
        "rejected_count": len(rejected),
        "rejected_sample": rejected[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract high-confidence verbatim programs into sidecar directories."
    )
    parser.add_argument(
        "--root",
        default="..",
        help="Project root directory (default: ..)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be extracted without modifying files",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Create sidecars and rewrite content.tex files",
    )
    parser.add_argument(
        "--report",
        default="build/temp/program_extraction_report.json",
        help="Path to JSON report (relative to root unless absolute)",
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    report_path = args.report
    if not os.path.isabs(report_path):
        report_path = os.path.join(root_dir, report_path)

    content_files = find_content_files(root_dir)
    if not content_files:
        print("No content.tex files found under 00_CONTENT/")
        return 1

    all_results = []
    total_accepted = 0
    total_rejected = 0

    for content_path in content_files:
        result = extract_from_file(content_path, root_dir, apply=args.apply)
        all_results.append(result)
        total_accepted += len(result["accepted"])
        total_rejected += result["rejected_count"]

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "total_files": len(content_files),
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "results": all_results,
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    mode_label = "Applied" if args.apply else "Dry run"
    print(f"{mode_label}: {total_accepted} programs extracted, {total_rejected} blocks skipped")
    print(f"Report: {os.path.relpath(report_path, root_dir).replace(chr(92), '/')}")

    for result in all_results:
        for item in result["accepted"]:
            print(f"  + {item['program_dir']} ({item['language']}) in {result['file']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
