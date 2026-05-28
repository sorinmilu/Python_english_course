"""Shared utilities for program sidecar detection, loading, and LaTeX rendering."""

from __future__ import annotations

import json
import os
import re
from string import Template
from typing import Any

LANGUAGE_EXTENSIONS = {
    "php": ".php",
    "c": ".c",
    "java": ".java",
    "javascript": ".js",
    "python": ".py",
}

MIN_NONEMPTY_LINES = 6  # more than 5 non-empty lines

TRACE_PATTERNS = (
    r"creates generator object",
    r"body has not run yet",
    r"top Python frame",
    r"top JS frame",
    r"top PHP frame",
    r"top JVM frame",
    r"caller continues",
    r"generator object remembers",
    r"active caller frame",
    r"state says where to resume",
    r"Fiber A\b",
    r"Fiber B\b",
    r"Generator object\b",
    r"^next\s*->",
)

BOX_DRAWING_RE = re.compile(r"\+[-+]+\+|^\s*\|[^|]+\|\s*$", re.MULTILINE)
TRACE_RES = [re.compile(p, re.IGNORECASE) for p in TRACE_PATTERNS]

VERBATIM_BLOCK_RE = re.compile(
    r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
    re.DOTALL,
)

def non_empty_lines(body: str) -> list[str]:
    return [line for line in body.splitlines() if line.strip()]


def count_non_empty_lines(body: str) -> int:
    return len(non_empty_lines(body))


def detect_language(body: str) -> tuple[str | None, float]:
    """Return (language, confidence) using strong markers only."""
    lines = non_empty_lines(body)
    if not lines:
        return None, 0.0

    sample = "\n".join(lines[:8])
    scores: dict[str, float] = {}

    if "<?php" in sample or re.search(r"\$\w+\s*=\s*new\s+Fiber\b", sample):
        scores["php"] = 0.95
    if re.search(r"function\s+\w+\s*\([^)]*\$\w+", sample):
        scores["php"] = max(scores.get("php", 0), 0.9)

    if re.search(r"#include\s*[<\"]", sample) or re.search(r"\bint\s+main\s*\(", sample):
        scores["c"] = 0.95
    if re.search(r"\bstruct\s+\w+\s*\{", sample):
        scores["c"] = max(scores.get("c", 0), 0.85)

    if re.search(r"\bimport\s+java\.", sample) or re.search(r"\bpublic\s+class\s+\w+", sample):
        scores["java"] = 0.95
    if re.search(r"\bpublic\s+static\s+void\s+main\s*\(", sample):
        scores["java"] = max(scores.get("java", 0), 0.9)

    if re.search(r"\bfunction\s*\*", sample) or re.search(r"\basync\s+function\b", sample):
        scores["javascript"] = 0.95
    if re.search(r"\bconsole\.\w+", sample):
        scores["javascript"] = max(scores.get("javascript", 0), 0.85)
    if re.search(r"\b(?:const|let)\s+\w+\s*=", sample) and "{" in sample:
        scores["javascript"] = max(scores.get("javascript", 0), 0.75)

    if re.search(r"^\s*(?:async\s+)?def\s+\w+\s*\(", sample, re.MULTILINE):
        scores["python"] = 0.95
    if re.search(r"\bimport\s+asyncio\b", sample) or re.search(r"\byield\b", sample):
        scores["python"] = max(scores.get("python", 0), 0.85)

    if not scores:
        return None, 0.0

    lang = max(scores, key=scores.get)
    return lang, scores[lang]


def is_diagram_or_trace(body: str) -> bool:
    if BOX_DRAWING_RE.search(body):
        return True

    trace_hits = sum(1 for pat in TRACE_RES if pat.search(body))
    lang, confidence = detect_language(body)
    if lang is None and trace_hits >= 2:
        return True
    if trace_hits >= 1 and confidence < 0.85:
        return True

    lines = non_empty_lines(body)
    arrow_lines = sum(
        1 for line in lines
        if re.match(r"^\s*(?:->|v\b|\.\.\.)", line.strip())
    )
    if arrow_lines >= 2 and confidence < 0.9:
        return True

    return False


def is_extractable_program(body: str) -> tuple[bool, str, str | None]:
    """Return (accepted, reason, language)."""
    if count_non_empty_lines(body) < MIN_NONEMPTY_LINES:
        return False, "too_few_lines", None

    if is_diagram_or_trace(body):
        return False, "diagram_or_trace", None

    lang, confidence = detect_language(body)
    if lang is None or confidence < 0.75:
        return False, "unknown_language", None

    return True, "ok", lang


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\\texttt\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-") or "program"


def section_prefix(content_dir_name: str) -> str:
    name = re.sub(r"^\d+_", "", content_dir_name)
    letters = re.sub(r"[^a-zA-Z]", "", name)
    return (letters[:3] or "pg").lower()


def make_slug(title: str, lang: str, used_slugs: set[str], prefix: str = "p") -> str:
    counter = 1
    while True:
        slug = f"{prefix}{counter:02d}"
        if slug not in used_slugs:
            used_slugs.add(slug)
            return slug
        counter += 1


def clean_latex_heading(text: str) -> str:
    text = re.sub(r"\\texttt\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    return text.strip()


def extract_last_heading_title(prose: str) -> str | None:
    command_re = re.compile(
        r"\\(?:paragraph|subsubsection|subsection|section)\s*\{",
        re.MULTILINE,
    )
    last_title = None
    for match in command_re.finditer(prose):
        start = match.end()
        depth = 1
        index = start
        while index < len(prose) and depth > 0:
            char = prose[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        if depth == 0:
            last_title = prose[start : index - 1]
    return last_title


def infer_title(prose_before: str, body: str, lang: str) -> str:
    heading = extract_last_heading_title(prose_before)
    if heading:
        title = clean_latex_heading(heading.strip())
        if len(title) > 80:
            title = title[:77].rstrip() + "..."
        return title

    lines = non_empty_lines(body)
    for line in lines[:5]:
        m = re.search(r"(?:def|function\*?|class|struct)\s+(\w+)", line)
        if m:
            return f"{lang.upper()} example: {m.group(1)}"

    return f"{lang.upper()} program example"


def escape_latex_title(text: str) -> str:
    text = clean_latex_heading(text)
    replacements = (
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def format_iobox_body(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(line.rstrip() + " \\\\" for line in lines)


def parse_program_token(token: str) -> tuple[str, dict[str, Any]]:
    """Parse 'programs/foo|linenos=false' into path and overrides."""
    if "|" in token:
        rel_path, param_str = token.split("|", 1)
        rel_path = rel_path.strip()
        overrides: dict[str, Any] = {}
        for part in param_str.split("|"):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.lower() in ("true", "false"):
                    overrides[key] = value.lower() == "true"
                else:
                    overrides[key] = value
            else:
                overrides[part] = True
        return rel_path, overrides
    return token.strip(), {}


def load_program_dir(program_dir: str) -> dict[str, Any]:
    json_path = os.path.join(program_dir, "program.json")
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"program.json not found in {program_dir}")

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    source_name = meta.get("file", "main.txt")
    source_path = os.path.join(program_dir, source_name)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Program source not found: {source_path}")

    with open(source_path, "r", encoding="utf-8") as f:
        meta["source_body"] = f.read()

    return meta


def render_program(
    program_dir: str,
    templates: dict[str, Template],
    overrides: dict[str, Any] | None = None,
) -> str:
    meta = load_program_dir(program_dir)
    overrides = overrides or {}

    language = meta["language"]
    title = escape_latex_title(meta["title"])
    label = meta["label"]
    linenos = overrides.get("linenos", meta.get("linenos", True))
    if "linenos" in overrides:
        linenos = overrides["linenos"]

    minted_options = "" if linenos else "linenos=false"
    code_body = meta["source_body"].rstrip("\n") + "\n"

    parts = [
        templates["program_codebox_template"].substitute(
            minted_options=minted_options,
            language=language,
            title=title,
            label=label,
            code_body=code_body,
        )
    ]

    input_text = meta.get("input")
    if input_text:
        parts.append(
            templates["program_inputbox_template"].substitute(
                input_body=input_text.rstrip("\n"),
            )
        )

    output_text = meta.get("output")
    if output_text:
        formatted = format_iobox_body(output_text)
        if formatted:
            parts.append(
                templates["program_outputbox_template"].substitute(
                    output_body=formatted,
                )
            )

    return "\n\n".join(parts) + "\n"


def write_program_sidecar(
    program_dir: str,
    meta: dict[str, Any],
    source_body: str,
) -> None:
    os.makedirs(program_dir, exist_ok=True)
    lang = meta["language"]
    ext = LANGUAGE_EXTENSIONS.get(lang, ".txt")
    source_name = meta.get("file") or f"main{ext}"
    if not source_name.startswith("main"):
        source_name = f"main{ext}"
    meta = {k: v for k, v in meta.items() if k != "source_body"}
    meta["file"] = source_name

    with open(os.path.join(program_dir, "program.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(os.path.join(program_dir, source_name), "w", encoding="utf-8") as f:
        f.write(source_body.rstrip("\n") + "\n")


def find_verbatim_blocks(content: str) -> list[dict[str, Any]]:
    blocks = []
    for match in VERBATIM_BLOCK_RE.finditer(content):
        body = match.group(1)
        if body.startswith("\n"):
            body = body[1:]
        if body.endswith("\n"):
            body = body[:-1]
        blocks.append(
            {
                "start": match.start(),
                "end": match.end(),
                "body": body,
                "full_match": match.group(0),
            }
        )
    return blocks


def detect_output_pair(content: str, block_end: int) -> tuple[str | None, int, int]:
    """If a following output verbatim exists, return (output_text, replace_start, replace_end)."""
    tail = content[block_end:]
    pattern = re.compile(
        r"^\s*(?:Output:|The output is approximately:)\s*"
        r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.match(tail)
    if not match:
        return None, 0, 0

    output_body = match.group(1)
    if output_body.startswith("\n"):
        output_body = output_body[1:]
    if output_body.endswith("\n"):
        output_body = output_body[:-1]

    replace_start = block_end + match.start()
    replace_end = block_end + match.end()
    return output_body, replace_start, replace_end
