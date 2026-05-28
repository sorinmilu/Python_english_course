#!/usr/bin/env python3
"""Compact web UI for running project-generation tools."""

from __future__ import annotations

import argparse
import atexit
import codecs
import json
import os
import re
import shutil
import signal
import urllib.error
import urllib.request
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from flask import Flask, jsonify, request, send_file, send_from_directory

from content_sync_utils import sync_content_tree
from course_synopsis_utils import (
    apply_reordered_tree,
    export_synopsis_tree_to_markdown,
    load_synopsis,
    save_synopsis,
    save_text_file_atomic,
    validate_tree,
)


SCRIPT_DIR = Path(__file__).resolve().parent
UI_DIR = SCRIPT_DIR / "ProjectManager"
BUILD_ARTIFACT_EXTENSIONS = {
    ".aux",
    ".bbl",
    ".bcf",
    ".bib",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".lof",
    ".log",
    ".lot",
    ".out",
    ".pdf",
    ".run.xml",
    ".synctex.gz",
    ".tex",
    ".toc",
}
HEADING_COMMANDS = {
    "chapter": 1,
    "section": 2,
    "subsection": 3,
    "subsubsection": 4,
}
FLOAT_ENVIRONMENTS = {"figure": "figure", "table": "table"}
# Float layouts that already imply a table or figure caption elsewhere; skip inner tabular.
_INVENTORY_SKIP_TABULAR_PARENTS = frozenset(
    {"table", "table*", "longtable", "figure", "figure*"}
)
_LATEX_BEGIN_END_RE = re.compile(r"\\(begin|end)\s*\{([^}]+)\}")
PDF_COMPRESSION_LEVELS = {"screen", "ebook", "printer", "prepress"}

PROOF_ALLOWED_MODELS = frozenset({"gpt-5.4-mini", "gpt-5.5"})
PROOF_CHATGPT_VISIT_SNAPSHOT_FILENAME = ".pm_proofread_visits.json"
PARAGRAPH_STYLE_VISIT_SNAPSHOT_FILENAME = ".pm_paragraph_style_visits.json"

PROOF_SYSTEM_PROMPT = """You are a professional LaTeX editor and linguistic expert.
Your task is to analyze the provided LaTeX content for spelling errors, grammatical mistakes, and stylistic improvements.

CRITICAL CONSTRAINTS:
1. PRESERVE LATEX: Never modify LaTeX commands, environments (e.g., \\begin{...}), or math mode content ($...$, \\[...\\]) unless there is a typo inside a text-based command like \\caption{...} or \\section{...}.
2. GRANULARITY: Provide edits as the smallest possible string segments so find-and-replace in a local Python app stays accurate.
3. CONTEXT: For every edit you must provide the exact 'original_text' substring as it appears in the source so the application can locate it. Use UNIQUE snippets whenever possible so each original_text occurs exactly once.
4. JSON ONLY: Your entire response must be a single JSON object. No conversational filler or markdown fences.

STYLISTIC GUIDELINES:
- type 'typo': spelling and basic grammar only.
- type 'reformulation': flow, academic tone, and clarity.

Respond with ONLY this JSON shape:
{\"edits\": [{\"original_text\": \"...\", \"replacement_text\": \"...\", \"type\": \"typo\" or \"reformulation\", \"explanation\": \"...\"}] }

Optional: include \"start\" and \"end\" as character offsets in the original source if helpful; fields are ignored by the UI if omitted.
"""

PARAGRAPH_STYLE_SYSTEM_PROMPT = r"""You are a senior academic editor specializing in STEM manuscripts and LaTeX formatting.
Your task is to analyze the provided LaTeX content paragraph by paragraph to improve clarity, logical flow, and academic tone.

CRITICAL CONSTRAINTS:
    1. PARAGRAPH-LEVEL ANALYSIS: Evaluate each paragraph as a whole. If the flow is clunky, the transitions are weak, or the tone is unacademic, propose a reformulation of the entire affected segment.
    2. PRESERVE LATEX INTEGRITY: You must keep all \cite{...}, \ref{...}, and math mode ($...$) structures intact within your reformulations. Do not change technical terminology.
    3. MAPPING ACCURACY: For every change, the 'original' field must contain the EXACT string (including whitespace and newlines) from the source text to ensure the Python find-and-replace function does not fail.
    4. JSON OUTPUT ONLY: Return a single JSON object with the following structure:
       {
         "edits": [
           {
             "original": "exact full paragraph or sentence from source",
             "replacement": "the reformulated version",
             "type": "reformulation",
             "reason": "short explanation of why this improves flow"
           }
         ]
       }

STYLISTIC GOALS:
    - Eliminate wordiness and passive voice where active voice is more direct.
    - Improve transitions between ideas (e.g., using "Furthermore," "In contrast," "Consequently").
    - Ensure a formal, objective academic tone suitable for a technical thesis.
"""

# Matches common LaTeX / natbib / biblatex citation commands; captures braced citation list.
_CITE_CMD_RE = re.compile(
    r"\\(?:"
    r"nocite|"
    r"cite[A-Za-z]*|Cite[A-Za-z]*|"
    r"[Pp]arencite|"
    r"[Tt]extcite|"
    r"[Ff]ootcite|"
    r"[Aa]utocite|"
    r"[Ff]ullcite"
    r")\*?"
    r"(?:\s*\[[^\]]*\])*"
    r"\s*\{([^}]*)\}"
)


def resolve_api_keys_path() -> Path:
    local = SCRIPT_DIR / "api_keys.json"
    if local.is_file():
        return local
    return SCRIPT_DIR.parent.parent / "Referat_1/03_Scripts/api_keys.json"


def load_openai_credentials() -> tuple[str, str]:
    path = resolve_api_keys_path()
    if not path.is_file():
        raise FileNotFoundError(f"API keys file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("api_keys.json root must be an object")
    section = data.get("openai")
    if not isinstance(section, dict):
        raise ValueError('api_keys.json must contain object "openai"')
    key = section.get("api_key")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("missing openai.api_key")
    raw_base = section.get("base_url")
    base = raw_base.strip() if isinstance(raw_base, str) and raw_base.strip() else "https://api.openai.com/v1"
    return key.strip(), base


def proof_canonical_relative_path(rel: Any) -> str:
    if not isinstance(rel, str):
        raise ValueError("relative_path must be a string")
    segment = rel.strip().replace("\\", "/")
    while segment.startswith("/"):
        segment = segment[1:]
    if not segment or ".." in Path(segment).parts:
        raise ValueError("invalid relative_path")
    if Path(segment).name != "content.tex":
        raise ValueError("relative_path must end with content.tex")
    return Path(*Path(segment).parts).as_posix()


def inspected_folder_to_content_relative(folder_raw: Any) -> str | None:
    if not isinstance(folder_raw, str):
        return None
    frag = folder_raw.strip().replace("\\", "/").strip("/").rstrip("/")
    if not frag or ".." in Path(frag).parts:
        return None
    return Path(frag).as_posix() + "/content.tex"


def proof_chatgpt_visit_snapshot_defaults() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "description": (
            "Visited content.tex paths (relative to main_project.json root_dir) analyzed via Proofreading ChatGPT "
            "in Project Manager."
        ),
        "visited": [],
    }


def proof_chatgpt_visits_parse_file(path: Path) -> set[str]:
    """Load visited-relative paths from disk; malformed entries skipped."""
    if not path.is_file():
        return set()
    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    raw_list = data.get("visited")
    if not isinstance(raw_list, list):
        return set()
    out: set[str] = set()
    for item in raw_list:
        if not isinstance(item, str):
            continue
        try:
            norm = proof_canonical_relative_path(item)
        except ValueError:
            continue
        if norm.endswith(".tex"):
            out.add(norm)
    return out


def proof_chatgpt_visits_write_atomic(path: Path, rels: set[str]) -> None:
    blob = proof_chatgpt_visit_snapshot_defaults()
    blob["visited"] = sorted(rels, key=lambda x: x.casefold())
    text = json.dumps(blob, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def paragraph_style_visit_snapshot_defaults() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "description": (
            "Visited content.tex paths (relative to main_project.json root_dir) analyzed via "
            "Paragraph-style (academic flow) ChatGPT in Project Manager."
        ),
        "visited": [],
    }


def paragraph_style_visits_write_atomic(path: Path, rels: set[str]) -> None:
    blob = paragraph_style_visit_snapshot_defaults()
    blob["visited"] = sorted(rels, key=lambda x: x.casefold())
    text = json.dumps(blob, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _strip_optional_json_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return t


def _parse_proof_edits_object(raw_json: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_json, dict):
        raise ValueError("model returned JSON that is not an object")
    edits_any = raw_json.get("edits")
    if not isinstance(edits_any, list):
        raise ValueError("JSON must contain array 'edits'")
    sane: list[dict[str, Any]] = []
    for i, edit in enumerate(edits_any):
        if not isinstance(edit, dict):
            raise ValueError(f"edit #{i + 1} is not an object")
        ot = edit.get("original_text")
        rt = edit.get("replacement_text")
        tp = edit.get("type")
        expl = edit.get("explanation", "")
        if not isinstance(ot, str):
            raise ValueError(f"edit #{i + 1} missing string original_text")
        if not isinstance(rt, str):
            raise ValueError(f"edit #{i + 1} missing string replacement_text")
        if tp not in ("typo", "reformulation"):
            raise ValueError(f"edit #{i + 1} type must be typo or reformulation")
        sane.append(
            {
                "original_text": ot,
                "replacement_text": rt,
                "type": tp,
                "explanation": expl if isinstance(expl, str) else str(expl),
            }
        )
    return sane


def _parse_paragraph_style_edits_object(raw_json: Any) -> list[dict[str, Any]]:
    """Normalize ChatGPT paragraph-style JSON into proof-compatible edit dicts."""
    if not isinstance(raw_json, dict):
        raise ValueError("model returned JSON that is not an object")
    edits_any = raw_json.get("edits")
    if not isinstance(edits_any, list):
        raise ValueError("JSON must contain array 'edits'")
    sane: list[dict[str, Any]] = []
    for i, edit in enumerate(edits_any):
        if not isinstance(edit, dict):
            raise ValueError(f"edit #{i + 1} is not an object")
        ot = edit.get("original")
        rt = edit.get("replacement")
        tp = edit.get("type")
        reason = edit.get("reason", "")
        if not isinstance(ot, str):
            raise ValueError(f"edit #{i + 1} missing string original")
        if not isinstance(rt, str):
            raise ValueError(f"edit #{i + 1} missing string replacement")
        if tp != "reformulation":
            raise ValueError(f"edit #{i + 1} type must be reformulation")
        sane.append(
            {
                "original_text": ot,
                "replacement_text": rt,
                "type": "reformulation",
                "explanation": reason if isinstance(reason, str) else str(reason),
            }
        )
    return sane


def _format_openai_http_error_body(
    raw: str,
    *,
    http_code: int,
    reason: str | None,
) -> str:
    """Turn OpenAI-compatible JSON error payloads into readable multi-line text."""
    head = f"HTTP {http_code}" + (f" {reason}" if reason else "")
    raw_stripped = raw.strip()
    if not raw_stripped:
        return head
    lines = [head]
    try:
        obj = json.loads(raw_stripped)
        err = obj.get("error")
        if isinstance(err, dict):
            if err.get("message"):
                lines.append(str(err["message"]))
            for key in ("type", "code", "param"):
                if err.get(key) is not None:
                    lines.append(f"{key}: {err[key]}")
        elif isinstance(err, str) and err.strip():
            lines.append(err.strip())
        else:
            lines.append(raw_stripped[:4000])
    except json.JSONDecodeError:
        lines.append(raw_stripped[:4000])
    return "\n".join(line for line in lines if line).strip()


def openai_chat_completions_proofread(*, api_key: str, base_url: str, model: str, document: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROOF_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "LaTeX source to analyze follows as plain text:\n\n" + document,
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            reply = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        msg = _format_openai_http_error_body(
            raw,
            http_code=exc.code,
            reason=getattr(exc, "reason", None),
        )
        raise RuntimeError(msg) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason or exc)) from exc

    try:
        content = reply["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("empty model content")
        content = _strip_optional_json_fences(content)
        parsed_any = json.loads(content)
        return _parse_proof_edits_object(parsed_any), warnings
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Unexpected OpenAI response shape: {type(exc).__name__}: {exc}") from exc


def openai_chat_completions_paragraph_style(
    *,
    api_key: str,
    base_url: str,
    model: str,
    document: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PARAGRAPH_STYLE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "LaTeX source to analyze follows as plain text:\n\n" + document,
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            reply = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        msg = _format_openai_http_error_body(
            raw,
            http_code=exc.code,
            reason=getattr(exc, "reason", None),
        )
        raise RuntimeError(msg) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason or exc)) from exc

    try:
        content = reply["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("empty model content")
        content = _strip_optional_json_fences(content)
        parsed_any = json.loads(content)
        return _parse_paragraph_style_edits_object(parsed_any), warnings
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Unexpected OpenAI response shape: {type(exc).__name__}: {exc}") from exc


def referat_content_dir(root_dir: Path) -> Path | None:
    """Resolve ``00_CONTENT`` relative to configured ``root_dir``."""
    candidates = (
        root_dir / "Referat_2" / "00_CONTENT",
        root_dir / "00_CONTENT",
    )
    for c in candidates:
        resolved = c.resolve()
        if resolved.is_dir():
            return resolved
    return None


def _split_flat_cite_tokens(arg: str) -> list[str]:
    tokens: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(arg):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            chunk = arg[start:i].strip()
            if chunk:
                tokens.append(chunk)
            start = i + 1
    tail = arg[start:].strip()
    if tail:
        tokens.append(tail)
    return tokens


def cite_tokens_from_line(line: str) -> set[str]:
    stripped = strip_latex_comment(line)
    out: set[str] = set()
    for m in _CITE_CMD_RE.finditer(stripped):
        for tok in _split_flat_cite_tokens(m.group(1)):
            t = tok.strip()
            if t:
                out.add(t)
    return out


def parse_missing_bib_database_keys(blg_text: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    prefix = "Warning--I didn't find a database entry for"
    for raw in blg_text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        m = re.search(
            rf"{re.escape(prefix)}\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))",
            line,
        )
        if not m:
            continue
        key = next((g for g in m.groups() if g), "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def scan_citation_occurrences(content_dir: Path, root_for_rel: Path, keys: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
    hits: dict[str, list[dict[str, Any]]] = {k: [] for k in keys}
    if not keys:
        return hits
    want: set[str] = set(keys)
    paths = sorted(
        set(content_dir.rglob("*.tex")) | set(content_dir.rglob("*.tikz")),
        key=lambda p: str(p).casefold(),
    )
    seen_hit: dict[str, set[tuple[str, int]]] = {k: set() for k in keys}

    for fp in paths:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(fp.resolve().relative_to(root_for_rel.resolve()))
        except ValueError:
            rel = str(fp.resolve())
        abs_path = str(fp.resolve())
        for lineno, line in enumerate(text.splitlines(), start=1):
            tokens = cite_tokens_from_line(line)
            for key in tokens & want:
                pair = (abs_path, lineno)
                if pair in seen_hit[key]:
                    continue
                seen_hit[key].add(pair)
                hits[key].append({"path": rel, "line": lineno})

    return hits


def strip_latex_comment(line: str) -> str:
    for idx, char in enumerate(line):
        if char != "%":
            continue
        slash_count = 0
        pos = idx - 1
        while pos >= 0 and line[pos] == "\\":
            slash_count += 1
            pos -= 1
        if slash_count % 2 == 0:
            return line[:idx]
    return line


def _skip_latex_spaces(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _skip_optional_latex_arg(text: str, pos: int) -> int:
    pos = _skip_latex_spaces(text, pos)
    if pos >= len(text) or text[pos] != "[":
        return pos
    depth = 0
    while pos < len(text):
        char = text[pos]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return pos + 1
        pos += 1
    return pos


def _read_latex_braced_arg(text: str, pos: int) -> tuple[str, int] | None:
    pos = _skip_latex_spaces(text, pos)
    if pos >= len(text) or text[pos] != "{":
        return None
    depth = 0
    start = pos + 1
    pos += 1
    while pos < len(text):
        char = text[pos]
        escaped = pos > 0 and text[pos - 1] == "\\"
        if char == "{" and not escaped:
            depth += 1
        elif char == "}" and not escaped:
            if depth == 0:
                return text[start:pos], pos + 1
            depth -= 1
        pos += 1
    return None


def find_latex_command_arg(text: str, command: str, start: int = 0) -> str:
    pattern = re.compile(rf"\\{re.escape(command)}\*?")
    match = pattern.search(text, start)
    if not match:
        return ""
    pos = _skip_optional_latex_arg(text, match.end())
    arg = _read_latex_braced_arg(text, pos)
    return arg[0].strip() if arg else ""


def compact_latex_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = re.sub(r"\\(?:textbf|textit|emph|MakeUppercase)\s*\{([^{}]*)\}", r"\1", text)
    return text


def find_first_label(text: str) -> str:
    match = re.search(r"\\label\s*\{([^{}]+)\}", text)
    return match.group(1).strip() if match else ""


def iter_latex_begin_end(line: str) -> list[tuple[str, str]]:
    """Ordered (begin|end, env_name) tokens on this line (comments stripped)."""
    clean = strip_latex_comment(line)
    found = [
        (m.start(), m.group(1), m.group(2).strip())
        for m in _LATEX_BEGIN_END_RE.finditer(clean)
    ]
    found.sort(key=lambda x: x[0])
    return [(op, env) for _, op, env in found]


def _match_env_close(stack: list[tuple[str, int]], env: str) -> int | None:
    for j in range(len(stack) - 1, -1, -1):
        if stack[j][0] == env:
            return j
    return None


def describe_float_like_block(block: str) -> tuple[str, str]:
    cap_raw = find_latex_command_arg(block, "caption")
    caption = compact_latex_text(cap_raw) if cap_raw.strip() else ""
    label = find_first_label(block).strip()
    return caption, label


def scan_tex_file_inventory(path: Path, want: str) -> list[dict[str, Any]]:
    """Parse one .tex / .tikz file for figures or tables (want: 'figures' | 'tables')."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    stack: list[tuple[str, int]] = []
    items: list[dict[str, Any]] = []

    for line_idx, line in enumerate(lines):
        for op, env in iter_latex_begin_end(line):
            if op == "begin":
                stack.append((env, line_idx))
                continue
            j = _match_env_close(stack, env)
            if j is None:
                continue
            start_line = stack[j][1]
            entry_env = stack[j][0]
            parents = {stack[k][0] for k in range(j)}
            stack = stack[:j]
            block = "\n".join(lines[start_line : line_idx + 1])
            caption, label = describe_float_like_block(block)

            if want == "figures":
                if entry_env not in ("figure", "figure*"):
                    continue
            elif entry_env in ("table", "table*", "longtable"):
                pass
            elif entry_env in ("tabular", "tabular*", "tabularx"):
                if parents & _INVENTORY_SKIP_TABULAR_PARENTS:
                    continue
            else:
                continue

            items.append(
                {
                    "env": entry_env,
                    "line": start_line + 1,
                    "caption": caption,
                    "label": label,
                }
            )

    return items


def build_content_inventory_groups(
    content_dir: Path,
    root_for_rel: Path,
    want: str,
) -> list[dict[str, Any]]:
    paths = sorted(
        set(content_dir.rglob("*.tex")) | set(content_dir.rglob("*.tikz")),
        key=lambda p: str(p).casefold(),
    )
    by_dir: dict[str, list[dict[str, Any]]] = {}
    for fp in paths:
        file_items = scan_tex_file_inventory(fp, want)
        if not file_items:
            continue
        try:
            rel = str(fp.resolve().relative_to(root_for_rel.resolve()))
        except ValueError:
            rel = str(fp.resolve())
        parent = str(Path(rel).parent.as_posix())
        by_dir.setdefault(parent, []).append(
            {
                "path": rel,
                "name": fp.name,
                "items": file_items,
            }
        )

    groups: list[dict[str, Any]] = []
    for dir_key in sorted(by_dir.keys(), key=lambda x: x.casefold()):
        files = sorted(by_dir[dir_key], key=lambda x: str(x.get("path", "")).casefold())
        groups.append({"dir": dir_key, "files": files})
    return groups


def content_inventory_payload(root_dir: Path, kind: str) -> dict[str, Any]:
    if kind not in ("figures", "tables"):
        raise ValueError("kind must be figures or tables")
    content = referat_content_dir(root_dir)
    if content is None:
        return {
            "ok": False,
            "error": "Could not find 00_CONTENT (under project root_dir or Referat_2/00_CONTENT)",
            "kind": kind,
            "groups": [],
            "content_root": "",
            "content_root_relative": "",
        }
    resolved = content.resolve()
    root_r = root_dir.resolve()
    try:
        rel_root = str(resolved.relative_to(root_r))
    except ValueError:
        rel_root = str(resolved)
    want = "figures" if kind == "figures" else "tables"
    groups = build_content_inventory_groups(resolved, root_r, want)
    return {
        "ok": True,
        "kind": kind,
        "label": "List of figures" if kind == "figures" else "List of tables",
        "groups": groups,
        "content_root": str(resolved),
        "content_root_relative": rel_root,
    }


def parse_heading_line(line: str) -> dict[str, Any] | None:
    clean = strip_latex_comment(line)
    match = re.search(r"\\(chapter|section|subsection|subsubsection)\*?", clean)
    if not match:
        return None
    command = match.group(1)
    title = find_latex_command_arg(clean, command, match.start())
    if not title:
        return None
    return {
        "type": command,
        "level": HEADING_COMMANDS[command],
        "title": compact_latex_text(title),
    }


def parse_float_block(kind: str, block: str, line_no: int) -> dict[str, Any] | None:
    caption = find_latex_command_arg(block, "caption")
    label = find_first_label(block)
    if not caption and not label:
        return None
    return {
        "type": kind,
        "label": label,
        "caption": compact_latex_text(caption),
        "line": line_no,
    }


def parse_latex_structure(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    roots: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    idx = 0
    while idx < len(lines):
        heading = parse_heading_line(lines[idx])
        if heading:
            label_scan = "\n".join(strip_latex_comment(line) for line in lines[idx : idx + 4])
            node = {
                **heading,
                "label": find_first_label(label_scan),
                "line": idx + 1,
                "children": [],
                "items": [],
            }
            while stack and int(stack[-1]["level"]) >= int(node["level"]):
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                roots.append(node)
            stack.append(node)

        clean = strip_latex_comment(lines[idx])
        begin = re.search(r"\\begin\s*\{(figure|table)\*?\}", clean)
        if begin:
            env = begin.group(1)
            block_lines = [lines[idx]]
            end_idx = idx
            while end_idx + 1 < len(lines):
                end_idx += 1
                block_lines.append(lines[end_idx])
                if re.search(rf"\\end\s*\{{{re.escape(env)}\*?\}}", strip_latex_comment(lines[end_idx])):
                    break
            item = parse_float_block(FLOAT_ENVIRONMENTS[env], "\n".join(block_lines), idx + 1)
            if item and stack:
                stack[-1]["items"].append(item)
            idx = end_idx

        idx += 1
    return roots


class ProjectManager:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path.expanduser().resolve()
        self.config = self._load_config(self.config_path)
        self.root_dir = self._resolve_root_dir(self.config, self.config_path)
        self.temp_dir = self._resolve_project_path(self.config.get("temp_dir", "build/temp"))
        self.main_latex_file = str(self.config.get("main_latex_file", "main_document.tex"))
        self.final_bibliography_file = str(
            self.config.get("final_bibliography_file", "full_references.bib")
        )
        self.processed_tex = self.temp_dir / self._processed_tex_name()
        self.processed_stem = self.processed_tex.stem
        self.processed_pdf = self.temp_dir / f"{self.processed_stem}.pdf"
        self.processed_blg = self.temp_dir / f"{self.processed_stem}.blg"
        self.processed_bib = self.temp_dir / self.final_bibliography_file
        self.papers_port = int(self.config.get("papers_port", 8080))

        self.lock = threading.RLock()
        self.runs: list[dict[str, Any]] = []
        self.web_tools: dict[str, dict[str, Any]] = {
            "papers": {
                "label": "Paper server",
                "port": self.papers_port,
                "url": f"http://127.0.0.1:{self.papers_port}",
                "expected_script": "papers_server.py",
                "process": None,
                "started_at": None,
                "error": "",
                "output": [],
            },
        }

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Config root must be a JSON object")
        return data

    def _save_config(self) -> None:
        """Persist in-memory config to config_path."""
        text = json.dumps(self.config, indent=2, ensure_ascii=False) + "\n"
        save_text_file_atomic(self.config_path, text.rstrip("\n"))

    def _sync_content_root(self) -> Path:
        """Resolve 00_CONTENT under root_dir from main_project.json."""
        content = referat_content_dir(self.root_dir)
        if content is None:
            raise ValueError(
                "Could not find 00_CONTENT under root_dir "
                f"({self.root_dir}); expected root_dir/00_CONTENT or "
                "root_dir/Referat_2/00_CONTENT"
            )
        return content.resolve()

    @staticmethod
    def _resolve_root_dir(config: dict[str, Any], config_path: Path) -> Path:
        raw = config.get("root_dir")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("Config must contain string root_dir")
        path = Path(raw.strip()).expanduser()
        if not path.is_absolute():
            path = (config_path.parent / path).resolve()
        else:
            path = path.resolve()
        if path.is_dir():
            return path
        # Fallback: repository root (parent of 03_Scripts)
        fallback = config_path.parent.parent.resolve()
        if fallback.is_dir():
            return fallback
        return path

    def _resolve_project_path(self, raw: Any) -> Path:
        path = Path(str(raw)).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.root_dir / path).resolve()

    def _processed_tex_name(self) -> str:
        path = Path(self.main_latex_file)
        if path.suffix == ".tex":
            return f"{path.stem}_processed.tex"
        return f"{path.name}_processed.tex"

    def project_payload(self) -> dict[str, Any]:
        content = referat_content_dir(self.root_dir)
        if content is not None:
            try:
                content_rel = str(content.resolve().relative_to(self.root_dir.resolve()))
            except ValueError:
                content_rel = str(content.resolve())
        else:
            content_rel = ""
        return {
            "config_path": str(self.config_path),
            "root_dir": str(self.root_dir),
            "build_dir": str(self.temp_dir),
            "processed_tex": str(self.processed_tex),
            "processed_tex_exists": self.processed_tex.is_file(),
            "processed_bib": str(self.processed_bib),
            "processed_bib_exists": self.processed_bib.is_file(),
            "processed_blg": str(self.processed_blg),
            "processed_blg_exists": self.processed_blg.is_file(),
            "processed_pdf": str(self.processed_pdf),
            "processed_pdf_exists": self.processed_pdf.is_file(),
            "pdf_url": "/pdf/main_document_processed.pdf",
            "content_dir_exists": content is not None,
            "content_root_relative": content_rel,
        }

    def source_payload(self, kind: str) -> dict[str, Any]:
        sources = {
            "latex": ("LaTeX source", self.processed_tex),
            "bibtex": ("BibTeX source", self.processed_bib),
            "blg": ("BibTeX errors", self.processed_blg),
        }
        if kind not in sources:
            raise ValueError(f"Unknown source type: {kind}")
        label, path = sources[kind]
        if not path.is_file():
            raise FileNotFoundError(f"{label} not found: {path}")
        return {
            "ok": True,
            "kind": kind,
            "label": label,
            "path": str(path),
            "text": path.read_text(encoding="utf-8", errors="replace"),
        }

    def bibtex_missing_refs_payload(self) -> dict[str, Any]:
        if not self.processed_blg.is_file():
            raise FileNotFoundError(f"BibTeX log not found: {self.processed_blg}")
        blg = self.processed_blg.read_text(encoding="utf-8", errors="replace")
        keys = parse_missing_bib_database_keys(blg)
        content = referat_content_dir(self.root_dir)
        result: dict[str, Any] = {
            "ok": True,
            "blg_path": str(self.processed_blg),
            "keys": [],
        }
        if not keys:
            result["content_root"] = ""
            return result

        if content is None:
            result["content_root"] = ""
            result["error"] = (
                "Could not find 00_CONTENT (under project root_dir or Referat_2/00_CONTENT)"
            )
            result["keys"] = [{"key": k, "occurrences": []} for k in keys]
            return result

        resolved = content.resolve()
        root_r = self.root_dir.resolve()
        result["content_root"] = str(resolved)
        try:
            result["content_root_relative"] = str(resolved.relative_to(root_r))
        except ValueError:
            result["content_root_relative"] = str(resolved)

        occ_map = scan_citation_occurrences(resolved, root_r, keys)
        result["keys"] = [
            {
                "key": key,
                "occurrences": sorted(
                    occ_map.get(key, []),
                    key=lambda row: (str(row.get("path", "")).casefold(), int(row.get("line") or 0)),
                ),
            }
            for key in keys
        ]
        return result

    def structure_payload(self) -> dict[str, Any]:
        if not self.processed_tex.is_file():
            raise FileNotFoundError(f"LaTeX source not found: {self.processed_tex}")
        text = self.processed_tex.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "label": "Document structure",
            "path": str(self.processed_tex),
            "tree": parse_latex_structure(text),
        }

    def content_inventory_payload(self, kind: str) -> dict[str, Any]:
        return content_inventory_payload(self.root_dir, kind)

    def compress_pdf(self, level: str) -> dict[str, Any]:
        level = str(level or "").strip().lower()
        if level not in PDF_COMPRESSION_LEVELS:
            raise ValueError(
                "Compression level must be one of: "
                + ", ".join(sorted(PDF_COMPRESSION_LEVELS))
            )
        if not self.processed_pdf.is_file():
            raise FileNotFoundError(f"PDF not found: {self.processed_pdf}")

        gs = shutil.which("gs")
        if not gs:
            raise RuntimeError("Ghostscript is not installed or 'gs' is not available on PATH")

        before_size = self.processed_pdf.stat().st_size
        tmp_pdf = self.processed_pdf.with_name(
            f".{self.processed_pdf.stem}.compressed-{uuid.uuid4().hex}.pdf"
        )
        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.5",
            f"-dPDFSETTINGS=/{level}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={tmp_pdf}",
            str(self.processed_pdf),
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.temp_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
                raise RuntimeError(detail or f"Ghostscript failed with exit code {result.returncode}")
            if not tmp_pdf.is_file() or tmp_pdf.stat().st_size <= 0:
                raise RuntimeError("Ghostscript did not produce a valid compressed PDF")
            after_size = tmp_pdf.stat().st_size
            os.replace(tmp_pdf, self.processed_pdf)
        finally:
            if tmp_pdf.exists():
                try:
                    tmp_pdf.unlink()
                except OSError:
                    pass

        return {
            "ok": True,
            "level": level,
            "before_size": before_size,
            "after_size": after_size,
        }

    def state_payload(self) -> dict[str, Any]:
        with self.lock:
            return {
                "ok": True,
                "project": self.project_payload(),
                "runs": [self._serialize_run(run) for run in self.runs],
                "tools": {
                    key: self._serialize_tool(key, tool)
                    for key, tool in self.web_tools.items()
                },
            }

    def _serialize_run(self, run: dict[str, Any]) -> dict[str, Any]:
        ended_at = run.get("ended_at")
        duration_until = ended_at or time.time()
        return {
            "id": run["id"],
            "action": run["action"],
            "name": run["name"],
            "status": run["status"],
            "started_at": run["started_at"],
            "started_label": run["started_label"],
            "ended_at": ended_at,
            "duration_seconds": max(0.0, duration_until - run["started_at"]),
            "returncode": run.get("returncode"),
            "output": "".join(run["chunks"]),
        }

    def _serialize_tool(self, key: str, tool: dict[str, Any]) -> dict[str, Any]:
        proc = tool.get("process")
        owned_process_alive = bool(proc and proc.poll() is None)
        if proc and not owned_process_alive:
            tool["process"] = None
            if proc.returncode and not tool.get("error"):
                tool["error"] = f"Process exited with code {proc.returncode}"
        owner = self._port_owner(int(tool["port"]))
        command = owner.get("command", "")
        pids = owner.get("pids", [])
        port_open = bool(owner.get("open"))
        expected = str(tool.get("expected_script", ""))

        if owned_process_alive and port_open:
            status = "owned"
            status_label = "owned running"
            pid = proc.pid
        elif owned_process_alive:
            status = "starting"
            status_label = "starting"
            pid = proc.pid
        elif port_open and expected and expected in command:
            status = "external"
            status_label = "running externally"
            pid = pids[0] if pids else None
        elif port_open:
            status = "occupied"
            status_label = "port occupied"
            pid = pids[0] if pids else None
        else:
            status = "stopped"
            status_label = "stopped"
            pid = None

        return {
            "key": key,
            "label": tool["label"],
            "status": status,
            "status_label": status_label,
            "running": status in {"owned", "external", "starting"},
            "port_open": port_open,
            "owned": status in {"owned", "starting"},
            "pid": pid,
            "pids": pids,
            "port": tool["port"],
            "url": tool["url"],
            "command": command,
            "started_at": tool.get("started_at") if owned_process_alive else None,
            "error": tool.get("error", ""),
            "output": "".join(tool.get("output", []))[-4000:],
            "can_start": not port_open and not owned_process_alive,
            "can_stop": status in {"owned", "starting"},
            "can_force_stop": status in {"external", "occupied"} and bool(pids),
        }

    def start_action(self, action: str) -> dict[str, Any]:
        if action == "generate_project":
            thread = threading.Thread(target=self._run_generate_project_sequence, daemon=True)
            thread.start()
            return {
                "id": "",
                "action": action,
                "name": "Generate project",
                "status": "running",
            }

        raise ValueError(f"Unknown action: {action}")

    def _new_run(self, action: str, name: str) -> dict[str, Any]:
        run = {
            "id": uuid.uuid4().hex,
            "action": action,
            "name": name,
            "status": "running",
            "started_at": time.time(),
            "started_label": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": None,
            "returncode": None,
            "chunks": [],
        }
        with self.lock:
            self.runs.append(run)
        return run

    def _generate_project_steps(self) -> list[dict[str, Any]]:
        return [
            {
                "label": "clean build artifacts",
                "cleanup": True,
                "cwd": self.temp_dir,
            },
            {
                "label": "generate_project.py",
                "cmd": [
                    sys.executable,
                    str(SCRIPT_DIR / "generate_project.py"),
                    str(self.config_path),
                ],
                "cwd": SCRIPT_DIR,
            },
            {
                "label": "pdflatex pass 1",
                "cmd": [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    self.processed_tex.name,
                ],
                "cwd": self.temp_dir,
            },
            {
                "label": "bibtex",
                "cmd": ["bibtex", self.processed_stem],
                "cwd": self.temp_dir,
                "continue_on_failure": True,
            },
            {
                "label": "pdflatex pass 2",
                "cmd": [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    self.processed_tex.name,
                ],
                "cwd": self.temp_dir,
            },
            {
                "label": "pdflatex pass 3",
                "cmd": [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    self.processed_tex.name,
                ],
                "cwd": self.temp_dir,
            },
        ]

    def _run_generate_project_sequence(self) -> None:
        steps = self._generate_project_steps()
        for idx, step in enumerate(steps, start=1):
            returncode = self._run_step_as_run(
                "generate_project",
                str(step["label"]),
                step,
                idx,
                len(steps),
            )
            if returncode != 0 and not step.get("continue_on_failure"):
                break

    def _run_step_as_run(
        self,
        action: str,
        name: str,
        step: dict[str, Any],
        idx: int,
        total: int,
    ) -> int:
        run = self._new_run(action, name)
        returncode = 0
        try:
            self._append(run, f"\n=== {step['label']} ({idx}/{total}) ===\n")
            if step.get("cleanup"):
                returncode = self._clean_build_artifacts(run, Path(step["cwd"]))
            else:
                self._append(run, f"$ {self._format_cmd(step['cmd'])}\n\n")
                returncode = self._run_process(run, step["cmd"], Path(step["cwd"]))
            self._append(run, f"\n--- exit code: {returncode} ---\n")
            if returncode != 0 and step.get("continue_on_failure"):
                self._append(
                    run,
                    "\n[project_manager] Non-zero BibTeX exit recorded as warning; "
                    "continuing with the next LaTeX pass.\n",
                )
        except Exception as exc:  # noqa: BLE001
            returncode = 1
            self._append(run, f"\n[project_manager] {type(exc).__name__}: {exc}\n")
        finally:
            status = "finished"
            if returncode != 0:
                status = "warning" if step.get("continue_on_failure") else "failed"
            self._finish_run(run, returncode, status)
        return returncode

    def _run_steps(self, run: dict[str, Any], steps: list[dict[str, Any]]) -> None:
        returncode = 0
        try:
            for idx, step in enumerate(steps, start=1):
                self._append(run, f"\n=== {step['label']} ({idx}/{len(steps)}) ===\n")
                if step.get("cleanup"):
                    returncode = self._clean_build_artifacts(run, Path(step["cwd"]))
                else:
                    self._append(run, f"$ {self._format_cmd(step['cmd'])}\n\n")
                    returncode = self._run_process(run, step["cmd"], Path(step["cwd"]))
                self._append(run, f"\n--- exit code: {returncode} ---\n")
                if returncode != 0:
                    break
        except Exception as exc:  # noqa: BLE001
            returncode = 1
            self._append(run, f"\n[project_manager] {type(exc).__name__}: {exc}\n")
        finally:
            self._finish_run(
                run,
                returncode,
                "finished" if returncode == 0 else "failed",
            )

    def _finish_run(self, run: dict[str, Any], returncode: int, status: str) -> None:
        with self.lock:
            run["returncode"] = returncode
            run["status"] = status
            run["ended_at"] = time.time()

    @staticmethod
    def _format_cmd(cmd: list[str]) -> str:
        return " ".join(str(part) for part in cmd)

    def _clean_build_artifacts(self, run: dict[str, Any], build_dir: Path) -> int:
        if not build_dir.exists():
            self._append(run, f"Build directory does not exist yet: {build_dir}\n")
            return 0
        if not build_dir.is_dir():
            self._append(run, f"[ERROR] Build path is not a directory: {build_dir}\n")
            return 1

        deleted = 0
        errors = 0
        for path in build_dir.rglob("*"):
            if not path.is_file() or not self._is_build_artifact(path):
                continue
            try:
                path.unlink()
                deleted += 1
                self._append(run, f"Deleted {path.relative_to(build_dir)}\n")
            except OSError as exc:
                errors += 1
                self._append(run, f"[ERROR] Could not delete {path}: {exc}\n")
        self._append(run, f"Cleaned {deleted} generated LaTeX/BibTeX/PDF file(s).\n")
        return 1 if errors else 0

    @staticmethod
    def _is_build_artifact(path: Path) -> bool:
        suffixes = "".join(path.suffixes[-2:]).lower()
        if suffixes in BUILD_ARTIFACT_EXTENSIONS:
            return True
        return path.suffix.lower() in BUILD_ARTIFACT_EXTENSIONS

    def _run_process(self, run: dict[str, Any], cmd: list[str], cwd: Path) -> int:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        assert proc.stdout is not None
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while True:
                chunk = proc.stdout.read(1)
                if chunk:
                    self._append(run, decoder.decode(chunk))
                    continue
                if proc.poll() is not None:
                    rest = proc.stdout.read()
                    if rest:
                        self._append(run, decoder.decode(rest))
                    tail = decoder.decode(b"", final=True)
                    if tail:
                        self._append(run, tail)
                    return int(proc.returncode or 0)
        except Exception:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            raise

    def _append(self, run: dict[str, Any], text: str) -> None:
        with self.lock:
            run["chunks"].append(text)

    def delete_run(self, run_id: str) -> bool:
        with self.lock:
            before = len(self.runs)
            self.runs = [run for run in self.runs if run["id"] != run_id]
            return len(self.runs) != before

    def clear_runs(self) -> None:
        with self.lock:
            if len(self.runs) <= 1:
                return
            latest = max(self.runs, key=lambda run: run["started_at"])
            self.runs = [latest]

    def inspected_content_tex_allowlist(self) -> frozenset[str]:
        out: set[str] = set()
        for folder in self.config.get("inspected_folders") or []:
            rel = inspected_folder_to_content_relative(folder)
            if rel:
                out.add(rel)
        return frozenset(out)

    def resolve_inspected_proof_tex(self, requested_relative_path: Any) -> Path:
        norm = proof_canonical_relative_path(requested_relative_path)
        if norm not in self.inspected_content_tex_allowlist():
            raise ValueError(f"path not permitted: {norm}")
        root_res = self.root_dir.resolve()
        segments = tuple(s for s in norm.split("/") if s)
        target = root_res.joinpath(*segments).resolve()
        try:
            rel_back = target.relative_to(root_res).as_posix()
        except ValueError as exc:
            raise ValueError("path escapes project root") from exc
        if rel_back != norm:
            raise ValueError("path normalization mismatch")
        if target.name != "content.tex":
            raise ValueError("not content.tex")
        return target

    def _proof_chatgpt_visit_snapshot_path(self) -> Path:
        return (self.root_dir / PROOF_CHATGPT_VISIT_SNAPSHOT_FILENAME).resolve()

    def proof_record_chatgpt_visit(self, canonical_relative: str) -> None:
        """Append path to persisted visit log after a successful Analyze call."""
        if canonical_relative not in self.inspected_content_tex_allowlist():
            return
        path = self._proof_chatgpt_visit_snapshot_path()
        with self.lock:
            current = proof_chatgpt_visits_parse_file(path)
            if canonical_relative in current:
                return
            current.add(canonical_relative)
            proof_chatgpt_visits_write_atomic(path, current)

    def proof_tree_payload(self) -> dict[str, Any]:
        visited_paths = proof_chatgpt_visits_parse_file(self._proof_chatgpt_visit_snapshot_path())
        items: list[dict[str, Any]] = []
        for rel in sorted(self.inspected_content_tex_allowlist(), key=lambda x: x.casefold()):
            tex_path = self.resolve_inspected_proof_tex(rel)
            items.append(
                {
                    "dir": str(Path(rel).parent.as_posix()),
                    "relative_path": rel,
                    "exists": tex_path.is_file(),
                    "visited": rel in visited_paths,
                }
            )
        return {
            "ok": True,
            "visit_snapshot": str(self._proof_chatgpt_visit_snapshot_path()),
            "items": items,
        }

    def proof_file_payload(self, relative_path: Any) -> dict[str, Any]:
        tex_path = self.resolve_inspected_proof_tex(relative_path)
        if not tex_path.is_file():
            raise FileNotFoundError(str(tex_path))
        try:
            text = tex_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = tex_path.read_text(encoding="utf-8", errors="replace")
            return {
                "ok": True,
                "relative_path": proof_canonical_relative_path(relative_path),
                "text": text,
                "warning": "file decoded with UTF-8 replacement characters",
            }
        return {
            "ok": True,
            "relative_path": proof_canonical_relative_path(relative_path),
            "text": text,
        }

    def proof_analyze_payload(self, relative_path: Any, model: Any) -> dict[str, Any]:
        if model not in PROOF_ALLOWED_MODELS:
            allowed = ", ".join(sorted(PROOF_ALLOWED_MODELS))
            raise ValueError(f"model must be one of: {allowed}")

        tex_path = self.resolve_inspected_proof_tex(relative_path)
        if not tex_path.is_file():
            raise FileNotFoundError(str(tex_path))

        api_key, base_url = load_openai_credentials()

        warnings: list[str] = []
        try:
            source = tex_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = tex_path.read_text(encoding="utf-8", errors="replace")
            warnings.append("source read with UTF-8 replacement")

        edits, api_warnings = openai_chat_completions_proofread(
            api_key=api_key,
            base_url=base_url,
            model=model,
            document=source,
        )
        warnings.extend(api_warnings)
        canonical = proof_canonical_relative_path(relative_path)
        try:
            self.proof_record_chatgpt_visit(canonical)
        except OSError as exc:
            warnings.append(f"could not save proofreading visit log: {exc}")

        payload: dict[str, Any] = {
            "ok": True,
            "relative_path": canonical,
            "edits": edits,
            "model": model,
        }
        if warnings:
            payload["warning"] = "; ".join(warnings)

        return payload

    def proof_apply_edit(self, relative_path: Any, original_text: str, replacement_text: str) -> dict[str, Any]:
        if not isinstance(original_text, str):
            raise ValueError("original_text must be string")
        if not isinstance(replacement_text, str):
            raise ValueError("replacement_text must be string")

        tex_path = self.resolve_inspected_proof_tex(relative_path)
        if not tex_path.is_file():
            raise FileNotFoundError(str(tex_path))

        if not original_text.strip():
            raise ValueError("original_text is empty")

        with self.lock:
            text = tex_path.read_text(encoding="utf-8")
            count = text.count(original_text)
            if count == 0:
                raise LookupError("original_text not found in file")
            if count > 1:
                raise LookupError(
                    "ambiguous: original_text appears more than once; refine the snippet"
                )
            new_text = text.replace(original_text, replacement_text, 1)
            tex_path.write_text(new_text, encoding="utf-8")

        return {"ok": True, "relative_path": proof_canonical_relative_path(relative_path)}

    def _paragraph_style_visit_snapshot_path(self) -> Path:
        return (self.root_dir / PARAGRAPH_STYLE_VISIT_SNAPSHOT_FILENAME).resolve()

    def paragraph_style_record_visit(self, canonical_relative: str) -> None:
        if canonical_relative not in self.inspected_content_tex_allowlist():
            return
        path = self._paragraph_style_visit_snapshot_path()
        with self.lock:
            current = proof_chatgpt_visits_parse_file(path)
            if canonical_relative in current:
                return
            current.add(canonical_relative)
            paragraph_style_visits_write_atomic(path, current)

    def paragraph_style_tree_payload(self) -> dict[str, Any]:
        visited_paths = proof_chatgpt_visits_parse_file(
            self._paragraph_style_visit_snapshot_path()
        )
        items: list[dict[str, Any]] = []
        for rel in sorted(self.inspected_content_tex_allowlist(), key=lambda x: x.casefold()):
            tex_path = self.resolve_inspected_proof_tex(rel)
            items.append(
                {
                    "dir": str(Path(rel).parent.as_posix()),
                    "relative_path": rel,
                    "exists": tex_path.is_file(),
                    "visited": rel in visited_paths,
                }
            )
        return {
            "ok": True,
            "visit_snapshot": str(self._paragraph_style_visit_snapshot_path()),
            "items": items,
        }

    def _course_synopsis_json_path(self) -> Path:
        """Locate ``course_synopsis.json``: ``initial_project_structure`` in config, then legacy keys, then default."""
        cfg_dir = self.config_path.parent
        default = (self.root_dir / "00_CONTENT" / "course_synopsis.json").resolve()

        ipc = self.config.get("initial_project_structure")
        if isinstance(ipc, dict):
            full = ipc.get("course_synopsis_path")
            if isinstance(full, str) and full.strip():
                candidate = Path(full.strip()).expanduser()
                if candidate.is_absolute():
                    return candidate.resolve()
                return (cfg_dir / candidate).resolve()
            dir_part = ipc.get("relative_path")
            fname_raw = ipc.get("course_synopsis") or ipc.get("course_synopsis_filename")
            if isinstance(fname_raw, str) and fname_raw.strip():
                leaf = Path(fname_raw.strip())
                if len(leaf.parts) > 1:
                    return (cfg_dir / leaf).resolve()
                rel_dir_s = ipc.get("relative_path")
                rel_base = (
                    Path(rel_dir_s.strip())
                    if isinstance(rel_dir_s, str) and rel_dir_s.strip()
                    else Path()
                )
                return (cfg_dir / rel_base / leaf).resolve()
            elif isinstance(dir_part, str) and dir_part.strip():
                # Directory only → default filename in that folder
                return (
                    cfg_dir / Path(dir_part.strip()) / "course_synopsis.json"
                ).resolve()

        legacy = self.config.get("course_synopsis_path")
        if isinstance(legacy, str) and legacy.strip():
            candidate = Path(legacy.strip()).expanduser()
            if candidate.is_absolute():
                return candidate.resolve()
            return (cfg_dir / candidate).resolve()

        return default

    @property
    def course_synopsis_path(self) -> Path:
        return self._course_synopsis_json_path()

    def _course_synopsis_path_relative(self) -> str:
        path = self.course_synopsis_path.resolve()
        root = self.root_dir.resolve()
        cfg_dir = self.config_path.parent.resolve()
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            pass
        try:
            return str(path.relative_to(cfg_dir)).replace("\\", "/")
        except ValueError:
            pass
        try:
            repo = cfg_dir.parent.resolve()
            return str(path.relative_to(repo)).replace("\\", "/")
        except ValueError:
            return path.as_posix()

    def course_synopsis_payload(self) -> dict[str, Any]:
        path = self.course_synopsis_path
        with self.lock:
            data = load_synopsis(path)
        return {
            "ok": True,
            "path": str(path),
            "path_relative": self._course_synopsis_path_relative(),
            "meta": data.get("meta") if isinstance(data.get("meta"), dict) else {},
            "tree": data.get("tree") if isinstance(data.get("tree"), list) else [],
        }

    def course_synopsis_reorder_payload(self, tree_input: Any) -> dict[str, Any]:
        if not isinstance(tree_input, list):
            raise ValueError("body.tree must be a JSON array")
        path = self.course_synopsis_path
        with self.lock:
            data = load_synopsis(path)
            merged = apply_reordered_tree(data, tree_input)
            save_synopsis(path, merged)
        return {
            "ok": True,
            "path": str(path),
            "path_relative": self._course_synopsis_path_relative(),
            "meta": merged.get("meta") if isinstance(merged.get("meta"), dict) else {},
            "tree": merged.get("tree") if isinstance(merged.get("tree"), list) else [],
        }

    @property
    def synopsis_full_markdown_export_path(self) -> Path:
        """``99_Markdowns/full_content.md`` next to repo root implied by ``03_Scripts`` config."""
        return (self.config_path.parent.parent / "99_Markdowns" / "full_content.md").resolve()

    def _synopsis_full_markdown_path_relative(self) -> str:
        path = self.synopsis_full_markdown_export_path.resolve()
        try:
            return str(path.relative_to(self.config_path.parent.parent.resolve())).replace(
                "\\", "/"
            )
        except ValueError:
            return path.as_posix()

    def course_synopsis_export_markdown_payload(self, tree_input: Any) -> dict[str, Any]:
        """Write the full client tree to ``99_Markdowns/full_content.md`` (ignores UI fold state)."""
        if not isinstance(tree_input, list):
            raise ValueError("body.tree must be a JSON array")
        if len(tree_input) == 0:
            raise ValueError("tree must not be empty")
        for item in tree_input:
            if not isinstance(item, dict):
                raise ValueError("tree items must be objects")

        markdown = export_synopsis_tree_to_markdown(tree_input)
        out_path = self.synopsis_full_markdown_export_path
        with self.lock:
            save_text_file_atomic(out_path, markdown)
        return {
            "ok": True,
            "path": str(out_path),
            "path_relative": self._synopsis_full_markdown_path_relative(),
            "characters": len(markdown),
        }

    def course_synopsis_sync_content_payload(
        self,
        tree_input: Any,
        *,
        rename_orphans: bool = False,
        dry_run: bool = False,
        confirm_orphan_rename: bool = False,
    ) -> dict[str, Any]:
        """Materialize synopsis tree under root_dir's 00_CONTENT and update inspected_folders."""
        path = self.course_synopsis_path
        if tree_input is None:
            with self.lock:
                data = load_synopsis(path)
            tree = data.get("tree") if isinstance(data.get("tree"), list) else []
        elif not isinstance(tree_input, list):
            raise ValueError("body.tree must be a JSON array")
        else:
            with self.lock:
                data = load_synopsis(path)
                merged = apply_reordered_tree(data, tree_input)
                tree = merged.get("tree") if isinstance(merged.get("tree"), list) else []

        validate_tree(tree)
        content_root = self._sync_content_root()
        root_r = self.root_dir.resolve()

        allow_rename = bool(self.config.get("content_sync_rename_orphans", False))
        if rename_orphans:
            allow_rename = True
        if confirm_orphan_rename:
            allow_rename = True

        with self.lock:
            sync_result = sync_content_tree(
                tree,
                content_root=content_root,
                root_dir=root_r,
                rename_orphans=allow_rename,
                dry_run=dry_run,
            )

            if not dry_run:
                self.config["inspected_folders"] = list(sync_result.inspected_folders)
                self._save_config()

        try:
            content_rel = str(content_root.relative_to(root_r))
        except ValueError:
            content_rel = str(content_root)

        return {
            "ok": True,
            "dry_run": dry_run,
            "content_root": str(content_root),
            "content_root_relative": content_rel.replace("\\", "/"),
            "inspected_folders": sync_result.inspected_folders,
            "created_dirs": sync_result.created_dirs,
            "skipped_dirs": sync_result.skipped_dirs,
            "created_files": sync_result.created_files,
            "skipped_files": sync_result.skipped_files,
            "renamed_orphans": sync_result.renamed_orphans,
            "pending_orphans": sync_result.pending_orphans,
        }

    def paragraph_style_analyze_payload(self, relative_path: Any, model: Any) -> dict[str, Any]:
        if model not in PROOF_ALLOWED_MODELS:
            allowed = ", ".join(sorted(PROOF_ALLOWED_MODELS))
            raise ValueError(f"model must be one of: {allowed}")

        tex_path = self.resolve_inspected_proof_tex(relative_path)
        if not tex_path.is_file():
            raise FileNotFoundError(str(tex_path))

        api_key, base_url = load_openai_credentials()

        warnings: list[str] = []
        try:
            source = tex_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = tex_path.read_text(encoding="utf-8", errors="replace")
            warnings.append("source read with UTF-8 replacement")

        edits, api_warnings = openai_chat_completions_paragraph_style(
            api_key=api_key,
            base_url=base_url,
            model=model,
            document=source,
        )
        warnings.extend(api_warnings)
        canonical = proof_canonical_relative_path(relative_path)
        try:
            self.paragraph_style_record_visit(canonical)
        except OSError as exc:
            warnings.append(f"could not save paragraph-style visit log: {exc}")

        payload: dict[str, Any] = {
            "ok": True,
            "relative_path": canonical,
            "edits": edits,
            "model": model,
        }
        if warnings:
            payload["warning"] = "; ".join(warnings)

        return payload

    def start_tool(self, key: str) -> dict[str, Any]:
        with self.lock:
            if key not in self.web_tools:
                raise ValueError(f"Unknown web tool: {key}")
            tool = self.web_tools[key]
            proc = tool.get("process")
            if proc and proc.poll() is None:
                return self._serialize_tool(key, tool)
            owner = self._port_owner(int(tool["port"]))
            if owner.get("open"):
                tool["error"] = (
                    f"Port {tool['port']} is already in use. "
                    "Use force stop if this is a stale tool process."
                )
                return self._serialize_tool(key, tool)
            tool["error"] = ""
            tool["output"] = []
            try:
                tool["process"] = self._spawn_tool(key)
                tool["started_at"] = time.time()
                threading.Thread(
                    target=self._capture_tool_output,
                    args=(key, tool["process"]),
                    daemon=True,
                ).start()
            except Exception as exc:  # noqa: BLE001
                tool["process"] = None
                tool["started_at"] = None
                tool["error"] = f"{type(exc).__name__}: {exc}"
            return self._serialize_tool(key, tool)

    def _spawn_tool(self, key: str) -> subprocess.Popen[bytes]:
        if key == "papers":
            cmd = [sys.executable, str(SCRIPT_DIR / "papers_server.py"), str(self.config_path)]
            cwd = SCRIPT_DIR
        else:
            raise ValueError(f"Unknown web tool: {key}")
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            start_new_session=True,
        )

    def _capture_tool_output(self, key: str, proc: subprocess.Popen[bytes]) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            if proc.stdout is None:
                return
            while True:
                chunk = proc.stdout.read(1)
                if chunk:
                    self._append_tool_output(key, decoder.decode(chunk))
                    continue
                if proc.poll() is not None:
                    rest = proc.stdout.read()
                    if rest:
                        self._append_tool_output(key, decoder.decode(rest))
                    tail = decoder.decode(b"", final=True)
                    if tail:
                        self._append_tool_output(key, tail)
                    break
        finally:
            with self.lock:
                tool = self.web_tools.get(key)
                if tool and tool.get("process") is proc and proc.returncode:
                    tool["error"] = f"Process exited with code {proc.returncode}"

    def _append_tool_output(self, key: str, text: str) -> None:
        with self.lock:
            tool = self.web_tools.get(key)
            if not tool:
                return
            output = tool.setdefault("output", [])
            output.append(text)
            joined = "".join(output)
            if len(joined) > 4000:
                tool["output"] = [joined[-4000:]]

    def stop_tool(self, key: str) -> dict[str, Any]:
        with self.lock:
            if key not in self.web_tools:
                raise ValueError(f"Unknown web tool: {key}")
            tool = self.web_tools[key]
            proc = tool.get("process")
            if proc and proc.poll() is None:
                self._terminate_process(proc)
            tool["process"] = None
            tool["started_at"] = None
            return self._serialize_tool(key, tool)

    @staticmethod
    def _terminate_process(proc: subprocess.Popen[Any]) -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (AttributeError, OSError):
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (AttributeError, OSError):
                proc.kill()
            proc.wait(timeout=5)

    def force_stop_tool(self, key: str) -> dict[str, Any]:
        with self.lock:
            if key not in self.web_tools:
                raise ValueError(f"Unknown web tool: {key}")
            tool = self.web_tools[key]
            proc = tool.get("process")
            if proc and proc.poll() is None:
                self._terminate_process(proc)
                tool["process"] = None
                tool["started_at"] = None
                tool["error"] = ""
                return self._serialize_tool(key, tool)

            owner = self._port_owner(int(tool["port"]))
            pids = [pid for pid in owner.get("pids", []) if pid != os.getpid()]
            if not pids:
                tool["error"] = f"No process id found for port {tool['port']}"
                return self._serialize_tool(key, tool)

        errors: list[str] = []
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                errors.append(f"{pid}: {exc}")
        deadline = time.time() + 3
        while time.time() < deadline and self._port_owner(int(tool["port"])).get("open"):
            time.sleep(0.1)
        if self._port_owner(int(tool["port"])).get("open"):
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError as exc:
                    errors.append(f"{pid}: {exc}")

        with self.lock:
            tool = self.web_tools[key]
            tool["process"] = None
            tool["started_at"] = None
            tool["error"] = "; ".join(errors)
            return self._serialize_tool(key, tool)

    def _port_owner(self, port: int) -> dict[str, Any]:
        pids = self._pids_for_port(port)
        commands = [self._command_for_pid(pid) for pid in pids]
        command = " | ".join(cmd for cmd in commands if cmd)
        return {
            "open": bool(pids) or self._port_is_open(port),
            "pids": pids,
            "command": command,
        }

    @staticmethod
    def _port_is_open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    @staticmethod
    def _pids_for_port(port: int) -> list[int]:
        try:
            result = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            pids = sorted({int(line) for line in result.stdout.splitlines() if line.strip().isdigit()})
            if pids:
                return pids
        except (OSError, ValueError):
            pass

        try:
            result = subprocess.run(
                ["ss", "-ltnp"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            return []

        pids: set[int] = set()
        for line in result.stdout.splitlines():
            if f":{port} " not in line and f":{port}\t" not in line:
                continue
            for match in re.finditer(r"pid=(\d+)", line):
                pids.add(int(match.group(1)))
        return sorted(pids)

    @staticmethod
    def _command_for_pid(pid: int) -> str:
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "args="],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            return ""
        return result.stdout.strip()

    def stop_all_tools(self) -> None:
        with self.lock:
            keys = list(self.web_tools)
        for key in keys:
            try:
                self.stop_tool(key)
            except Exception:
                pass


def _proof_analyze_error_payload(exc: BaseException) -> dict[str, Any]:
    import traceback

    et = type(exc).__name__
    msg = str(exc).strip() or et
    detail_parts = [f"{et}: {msg}"]
    if not isinstance(exc, (ValueError, FileNotFoundError, RuntimeError)):
        detail_parts.append(traceback.format_exc())
    return {
        "ok": False,
        "error": msg[:800],
        "detail": "\n\n".join(detail_parts).strip(),
        "error_type": et,
    }


def create_app(manager: ProjectManager) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(UI_DIR / "templates"),
        static_folder=str(UI_DIR / "static"),
    )

    @app.after_request
    def _no_cache_static(response):
        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response

    @app.get("/")
    def index():
        return send_from_directory(UI_DIR / "templates", "index.html")

    @app.get("/api/state")
    def api_state():
        return jsonify(manager.state_payload())

    @app.post("/api/actions/<action>")
    def api_action(action: str):
        try:
            run = manager.start_action(action)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "run": run})

    @app.delete("/api/runs/<run_id>")
    def api_delete_run(run_id: str):
        deleted = manager.delete_run(run_id)
        return jsonify({"ok": True, "deleted": deleted})

    @app.post("/api/runs/clear")
    def api_clear_runs():
        manager.clear_runs()
        return jsonify({"ok": True})

    @app.post("/api/tools/<tool>/<operation>")
    def api_tool(tool: str, operation: str):
        try:
            if operation == "start":
                payload = manager.start_tool(tool)
            elif operation == "stop":
                payload = manager.stop_tool(tool)
            elif operation == "force_stop":
                payload = manager.force_stop_tool(tool)
            else:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "operation must be start, stop, or force_stop",
                        }
                    ),
                    400,
                )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "tool": payload})

    @app.get("/api/source/<kind>")
    def api_source(kind: str):
        try:
            return jsonify(manager.source_payload(kind))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @app.get("/api/bibtex/missing-refs")
    def api_bibtex_missing_refs():
        try:
            return jsonify(manager.bibtex_missing_refs_payload())
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @app.get("/api/structure")
    def api_structure():
        try:
            return jsonify(manager.structure_payload())
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @app.get("/api/content/inventory/<kind>")
    def api_content_inventory(kind: str):
        try:
            return jsonify(manager.content_inventory_payload(kind))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/pdf/compress")
    def api_pdf_compress():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(manager.compress_pdf(str(body.get("level") or "ebook")))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/proof/tree")
    def api_proof_tree():
        return jsonify(manager.proof_tree_payload())

    @app.get("/api/proof/file")
    def api_proof_file():
        rel = request.args.get("path", "")
        try:
            return jsonify(manager.proof_file_payload(rel))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @app.post("/api/proof/analyze")
    def api_proof_analyze():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(manager.proof_analyze_payload(body.get("relative_path"), body.get("model")))
        except ValueError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 400
        except FileNotFoundError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 404
        except RuntimeError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 502
        except Exception as exc:  # noqa: BLE001
            return jsonify(_proof_analyze_error_payload(exc)), 500

    @app.post("/api/proof/apply-edit")
    def api_proof_apply_edit():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(
                manager.proof_apply_edit(
                    body.get("relative_path"),
                    str(body.get("original_text") or ""),
                    str(body.get("replacement_text") or ""),
                )
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except LookupError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409

    @app.get("/api/paragraph-style/tree")
    def api_paragraph_style_tree():
        return jsonify(manager.paragraph_style_tree_payload())

    @app.post("/api/paragraph-style/analyze")
    def api_paragraph_style_analyze():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(
                manager.paragraph_style_analyze_payload(
                    body.get("relative_path"), body.get("model")
                )
            )
        except ValueError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 400
        except FileNotFoundError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 404
        except RuntimeError as exc:
            return jsonify(_proof_analyze_error_payload(exc)), 502
        except Exception as exc:  # noqa: BLE001
            return jsonify(_proof_analyze_error_payload(exc)), 500

    @app.post("/api/paragraph-style/apply-edit")
    def api_paragraph_style_apply_edit():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(
                manager.proof_apply_edit(
                    body.get("relative_path"),
                    str(body.get("original_text") or ""),
                    str(body.get("replacement_text") or ""),
                )
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except LookupError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409

    @app.get("/api/course-synopsis")
    def api_course_synopsis():
        try:
            return jsonify(manager.course_synopsis_payload())
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/course-synopsis/reorder")
    def api_course_synopsis_reorder():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(manager.course_synopsis_reorder_payload(body.get("tree")))
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/course-synopsis/export-markdown")
    def api_course_synopsis_export_markdown():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(manager.course_synopsis_export_markdown_payload(body.get("tree")))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/course-synopsis/sync-content")
    def api_course_synopsis_sync_content():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(
                manager.course_synopsis_sync_content_payload(
                    body.get("tree"),
                    rename_orphans=bool(body.get("rename_orphans")),
                    dry_run=bool(body.get("dry_run")),
                    confirm_orphan_rename=bool(body.get("confirm_orphan_rename")),
                )
            )
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/pdf/main_document_processed.pdf")
    def api_pdf():
        if not manager.processed_pdf.is_file():
            return jsonify({"ok": False, "error": "PDF not found"}), 404
        return send_file(manager.processed_pdf, mimetype="application/pdf")

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to main_project.json")
    parser.add_argument("--host", default="127.0.0.1", help="Host for this manager")
    parser.add_argument("--port", type=int, default=5055, help="Port for this manager")
    args = parser.parse_args(argv)

    manager = ProjectManager(args.config)
    atexit.register(manager.stop_all_tools)
    app = create_app(manager)
    print(f"Project manager: http://{args.host}:{args.port}")
    print(f"Config: {manager.config_path}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
