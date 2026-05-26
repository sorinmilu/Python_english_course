#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
papers_server.py

Usage:
    python papers_server.py config.json

What it does:
- Reads JSON config with keys: root_dir, inspected_folders, papers_dir, papers_port,
  bibliography_file (name like "references.bib").
- Builds a folder tree from inspected_folders.
- For each folder containing the bibliography file, parses BibTeX entries and
  lists them in a table (year, bibtex_label, authors, title + PDF link).
- Starts an HTTP server on papers_port. Serves:
    - "/" -> generated HTML page
    - any other path -> static files under root_dir (PDFs included)

No external dependencies.
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from http.server import SimpleHTTPRequestHandler, HTTPServer
from functools import partial
from urllib.parse import quote, parse_qs
import html
import datetime
import re
import sys
import threading
import subprocess

# Import sync manager
try:
    from sync_manager import SyncManager
except ImportError:
    SyncManager = None

# --------------------------- BibTeX parsing (no deps) ---------------------------

class BibEntry:
    def __init__(self, entry_type: str, key: str, fields: Dict[str, str], bib_path: Path):
        self.entry_type = entry_type
        self.key = key
        self.fields = {k.lower(): v for k, v in fields.items()}
        self.bib_path = bib_path  # path to references.bib

    @property
    def year(self) -> str:
        y = self.fields.get("year", "").strip()
        if not y:
            # Try date like 2016-05-21
            date = self.fields.get("date", "").strip()
            m = re.match(r"(\d{4})", date)
            if m:
                return m.group(1)
        return y or ""

    @property
    def authors(self) -> str:
        # Keep raw author string but make it compact-ish
        a = self.fields.get("author", "").strip()
        return re.sub(r"\s+", " ", a)

    @property
    def title(self) -> str:
        t = self.fields.get("title", "").strip()
        return re.sub(r"\s+", " ", t)

    def extract_pdf_candidate(self) -> Optional[str]:
        """
        Look for a local PDF path in 'file' (Zotero/Mendeley formats allowed) or 'pdf' field.
        Return the *raw* path string if found, else None.
        """
        # Priority 1: file field
        file_field = self.fields.get("file")
        candidates: List[str] = []
        if file_field:
            # Common patterns include "path/to/file.pdf", "something:file.pdf:pdf", or multiple separated by ';'
            # Find any token ending with .pdf (case-insensitive)
            for m in re.finditer(r"([^;:\|\{\}]+?\.pdf)\b", file_field, flags=re.IGNORECASE):
                candidates.append(m.group(1).strip())
        # Priority 2: pdf field (some entries use 'pdf = {...}')
        pdf_field = self.fields.get("pdf")
        if pdf_field and pdf_field.lower().endswith(".pdf"):
            candidates.append(pdf_field.strip())

        return candidates[0] if candidates else None

def _strip_braces_quotes(v: str) -> str:
    v = v.strip().strip(',')
    # Remove one level of wrapping {...} or "..."
    if (v.startswith("{") and v.endswith("}")) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1]
    return v.strip()

def parse_bibtex_entries(bib_path: Path) -> List[BibEntry]:
    """
    Minimal BibTeX parser robust enough for typical .bib files:
    - Finds entries like @type{key, field = {value}, ...}
    - Balances braces to capture entry blocks
    - Parses fields at top level (respects braces/quotes)
    """
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    i, n = 0, len(text)
    entries: List[BibEntry] = []

    while True:
        at = text.find("@", i)
        if at == -1:
            break
        # Read entry type
        j = at + 1
        while j < n and text[j].isalpha():
            j += 1
        entry_type = text[at+1:j].strip().lower()
        # Skip whitespace until '{'
        while j < n and text[j].isspace():
            j += 1
        if j >= n or text[j] != "{":
            i = j
            continue
        # Capture block with balanced braces
        depth = 0
        start = j + 1
        k = j
        while k < n:
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    # Block ends just before this closing brace; we started after the opening one.
                    end = k
                    break
            k += 1
        else:
            # Unbalanced; abort this entry
            i = j + 1
            continue

        block = text[start:end].strip()
        # First token until first comma at top-level => key
        key, fields_str = _split_key_and_fields(block)
        if key:
            fields = _parse_fields(fields_str)
            entries.append(BibEntry(entry_type, key.strip(), fields, bib_path))
        i = end + 1

    return entries

def _split_key_and_fields(block: str) -> Tuple[str, str]:
    depth = 0
    for idx, ch in enumerate(block):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "," and depth == 0:
            return block[:idx].strip(), block[idx+1:].strip()
    # No comma found; malformed
    return block.strip(), ""

def _parse_fields(s: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    i, n = 0, len(s)
    while i < n:
        # Skip separators/whitespace
        while i < n and s[i] in ", \t\r\n":
            i += 1
        # Read field name
        start = i
        while i < n and (s[i].isalnum() or s[i] in "_-"):
            i += 1
        name = s[start:i].strip()
        if not name:
            break
        # Skip spaces
        while i < n and s[i].isspace():
            i += 1
        if i >= n or s[i] != "=":
            # Malformed, try to recover by skipping to next comma
            i = s.find(",", i)
            if i == -1:
                break
            i += 1
            continue
        i += 1  # skip '='
        # Skip spaces
        while i < n and s[i].isspace():
            i += 1
        # Read value: may be {...}, "..." or bare until comma at depth 0
        if i < n and s[i] in "{'\"":
            quote_char = s[i]
            if quote_char == "{":
                depth = 0
                val_start = i
                while i < n:
                    if s[i] == "{":
                        depth += 1
                    elif s[i] == "}":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                val = s[val_start:i]
            else:
                # quoted
                i += 1
                val_start = i
                while i < n and s[i] != quote_char:
                    # allow escaped quotes
                    if s[i] == "\\" and i + 1 < n:
                        i += 2
                    else:
                        i += 1
                val = '"' + s[val_start:i] + '"'
                if i < n:  # skip closing quote
                    i += 1
        else:
            # bare value
            val_start = i
            depth = 0
            while i < n:
                ch = s[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                elif ch == "," and depth == 0:
                    break
                i += 1
            val = s[val_start:i].strip()
        fields[name] = _strip_braces_quotes(val)
        # move past trailing comma if present
        if i < n and s[i] == ",":
            i += 1
    return fields

# --------------------------- Tree model ---------------------------

class TreeNode:
    def __init__(self, name: str, rel_path: Path):
        self.name = name
        self.rel_path = rel_path  # path relative to root_dir
        self.children: Dict[str, TreeNode] = {}
        self.entries: List[BibEntry] = []  # present if this folder has a references.bib

    def ensure_child(self, name: str, rel_path: Path) -> "TreeNode":
        if name not in self.children:
            self.children[name] = TreeNode(name, rel_path)
        return self.children[name]

# --------------------------- Building data ---------------------------

def build_tree_from_config(cfg: dict) -> Tuple[TreeNode, Path, Path, str]:
    root_dir = Path(cfg["root_dir"]).resolve()
    inspected: List[str] = cfg.get("inspected_folders", [])
    bib_name = cfg.get("bibliography_file", "references.bib")
    papers_dir = root_dir / cfg.get("papers_dir", "")
    root = TreeNode(name=root_dir.name, rel_path=Path("."))

    for folder in inspected:
        rel = Path(folder)
        # Normalize to POSIX-like semantics; keep rel path as given
        abs_folder = (root_dir / rel).resolve()
        # Build nodes along the path components
        cur = root
        accum = Path(".")
        for comp in rel.parts:
            if comp in ("/", "\\"):
                continue
            accum = accum / comp
            cur = cur.ensure_child(comp, accum)

        # If this folder has the bibliography file, parse it
        bib_path = abs_folder / bib_name
        if bib_path.exists():
            try:
                cur.entries = parse_bibtex_entries(bib_path)
            except Exception as e:
                print(f"[WARN] Failed to parse {bib_path}: {e}", file=sys.stderr)

    return root, root_dir, papers_dir, bib_name

# --------------------------- PDF resolution ---------------------------

class PdfResolver:
    def __init__(self, root_dir: Path, papers_dir: Path):
        self.root_dir = root_dir
        self.papers_dir = papers_dir
        self._cache: Dict[str, Optional[Path]] = {}

    def resolve(self, entry: BibEntry) -> Optional[Path]:
        raw = entry.extract_pdf_candidate()
        if not raw:
            return None
        cache_key = f"{entry.bib_path}::{raw}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        raw = raw.replace("\\", "/").strip()
        # If 'raw' looks like an http(s) URL, don't try to serve it locally
        if re.match(r"^https?://", raw, re.IGNORECASE):
            self._cache[cache_key] = None
            return None

        # Try relative to the bib file directory
        p1 = (entry.bib_path.parent / raw).resolve()
        if p1.exists() and p1.is_file():
            self._cache[cache_key] = p1
            return p1

        # If only a filename was provided, look under papers_dir (breadth-first glob)
        fname = Path(raw).name
        p2 = self.papers_dir / fname
        if p2.exists() and p2.is_file():
            self._cache[cache_key] = p2.resolve()
            return p2.resolve()

        # Fallback: search recursively under papers_dir (might be slower, cache result)
        try:
            for hit in self.papers_dir.rglob(fname):
                if hit.is_file():
                    self._cache[cache_key] = hit.resolve()
                    return hit.resolve()
        except Exception:
            pass

        self._cache[cache_key] = None
        return None

# --------------------------- HTML rendering ---------------------------

PDF_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" aria-label="PDF" role="img">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="currentColor" opacity="0.2"/>
  <path d="M14 2v6h6" fill="none" stroke="currentColor" stroke-width="2"/>
  <text x="8" y="17" font-family="Arial, Helvetica, sans-serif" font-size="7" fill="currentColor">PDF</text>
</svg>
"""

CSS = """
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; line-height: 1.5; }
h1,h2,h3,h4,h5,h6 { margin: 1.2rem 0 0.5rem; }
section { margin-bottom: 1.5rem; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; }
th, td { border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }
th { background: #f7f7f7; text-align: left; }
.folder-path { color: #666; font-size: 0.9rem; }
.title-cell a.title { text-decoration: none; }
.title-cell a.pdf { margin-left: 6px; vertical-align: text-bottom; display: inline-flex; align-items: center; }
small.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; color: #555; }
footer { margin-top: 2rem; color: #777; font-size: 0.9rem; }
/* Collapsible sections */
.section-header { display: flex; align-items: center; gap: 0.5rem; }
.toggle-btn { background: none; border: 1px solid #ddd; border-radius: 4px; padding: 2px 6px; cursor: pointer; font-size: 0.9rem; line-height: 1; }
.toggle-btn:focus { outline: 2px solid #66aaff; }
.section.collapsed > .section-body { display: none; }
.section-body { margin-left: 1rem; }
/* Global controls */
.global-controls { margin: 0.8rem 0 1rem; display:flex; gap:0.5rem; }
.global-btn { background: none; border: 1px solid #ddd; border-radius: 4px; padding: 4px 8px; cursor: pointer; }
.global-btn:focus { outline: 2px solid #66aaff; }
/* Sync banner */
#sync-banner { margin: 1rem 0; padding: 0.8rem; background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; display: block; }
#sync-banner.error { background: #ffe0e0; border-color: #ff9999; }
#sync-banner.dirty { background: #fff4e0; border-color: #ffcc99; }
#sync-banner.active { background: #e0f0ff; border-color: #99ccff; }
.sync-controls { display: flex; align-items: center; gap: 0.5rem; }
.sync-status { flex: 1; }
.sync-btn { background: #4a90e2; color: white; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-size: 0.9rem; }
.sync-btn:hover { background: #357abd; }
.sync-btn:disabled { background: #ccc; cursor: not-allowed; }
"""

JS = """
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('section.section').forEach(function(sec) {
        // ensure initial state (expanded)
        var btn = sec.querySelector('.toggle-btn');
        if (!btn) return;
        btn.addEventListener('click', function(e) {
            var collapsed = sec.classList.toggle('collapsed');
            btn.setAttribute('aria-expanded', (!collapsed).toString());
            btn.textContent = collapsed ? '\u25B6' : '\u25BC';
        });
    });
    // global controls
    var exp = document.getElementById('expand-all');
    var col = document.getElementById('collapse-all');
    function expandAll() {
        document.querySelectorAll('section.section').forEach(function(sec){
            sec.classList.remove('collapsed');
            var b = sec.querySelector('.toggle-btn');
            if (b) { b.setAttribute('aria-expanded','true'); b.textContent = '\u25BC'; }
        });
    }
    function collapseAll() {
        document.querySelectorAll('section.section').forEach(function(sec){
            sec.classList.add('collapsed');
            var b = sec.querySelector('.toggle-btn');
            if (b) { b.setAttribute('aria-expanded','false'); b.textContent = '\u25B6'; }
        });
    }
    if (exp) exp.addEventListener('click', expandAll);
    if (col) col.addEventListener('click', collapseAll);
    
    // Sync status polling and controls
    var syncBanner = document.getElementById('sync-banner');
    var syncStatus = document.getElementById('sync-status');
    var syncPushBtn = document.getElementById('sync-push-btn');
    var syncAuthBtn = document.getElementById('sync-auth-btn');
    
    if (syncBanner) {
        function updateSyncStatus() {
            fetch('/sync/status')
                .then(function(res) { 
                    if (!res.ok) {
                        console.error('Sync status request failed:', res.status);
                        return null;
                    }
                    return res.json(); 
                })
                .then(function(data) {
                    if (!data) return;
                    if (data.error && data.error === "Sync not configured") {
                        syncBanner.style.display = 'none';
                        return;
                    }
                    
                    var stage = data.stage || 'idle';
                    var message = data.message || '';
                    var dirty = data.dirty || false;
                    var dirtyCount = data.dirty_count || 0;
                    
                    // Update status message
                    if (syncStatus) {
                        var statusText = '';
                        if (stage === 'auth_needed') {
                            statusText = 'Authentication required';
                        } else if (stage === 'auth_running') {
                            statusText = 'Authenticating...';
                        } else if (stage === 'pulling') {
                            statusText = 'Pulling files...';
                        } else if (stage === 'pushing') {
                            statusText = 'Pushing files...';
                        } else if (stage === 'error') {
                            statusText = 'Error: ' + (message || 'Unknown error');
                        } else if (dirty) {
                            statusText = dirtyCount + ' file(s) pending push';
                        } else {
                            statusText = 'Synced';
                        }
                        syncStatus.textContent = statusText;
                    }
                    
                    // Update push button (always visible, update text based on state)
                    if (syncPushBtn) {
                        syncPushBtn.style.display = 'inline-block';
                        if (stage === 'pushing') {
                            syncPushBtn.textContent = 'Pushing...';
                            syncPushBtn.disabled = true;
                        } else if (dirty && dirtyCount > 0) {
                            syncPushBtn.textContent = 'Push (' + dirtyCount + ')';
                            syncPushBtn.disabled = false;
                        } else {
                            syncPushBtn.textContent = 'Push';
                            syncPushBtn.disabled = false;
                        }
                    }
                    
                    // Show/hide auth button
                    if (syncAuthBtn) {
                        if (stage === 'auth_needed') {
                            syncAuthBtn.style.display = 'inline-block';
                        } else {
                            syncAuthBtn.style.display = 'none';
                        }
                    }
                    
                    // Always show banner (unless sync not configured)
                    syncBanner.style.display = 'block';
                    
                    // Update banner styling based on state
                    syncBanner.className = 'sync-banner';
                    if (stage === 'error') {
                        syncBanner.classList.add('error');
                    } else if (dirty) {
                        syncBanner.classList.add('dirty');
                    } else if (stage === 'auth_running' || stage === 'pulling' || stage === 'pushing') {
                        syncBanner.classList.add('active');
                    }
                })
                .catch(function(err) {
                    console.error('Sync status error:', err);
                });
        }
        
        // Poll every 2 seconds
        updateSyncStatus();
        setInterval(updateSyncStatus, 2000);
        
        // Button handlers
        if (syncPushBtn) {
            syncPushBtn.addEventListener('click', function() {
                fetch('/sync/push', {method: 'POST'})
                    .then(function() { updateSyncStatus(); });
            });
        }
        
        if (syncAuthBtn) {
            syncAuthBtn.addEventListener('click', function() {
                fetch('/sync/auth', {method: 'POST'})
                    .then(function() { updateSyncStatus(); });
            });
        }
        
    }
});
"""

def render_html(root: TreeNode, root_dir: Path, resolver: PdfResolver, sync_manager: Optional[SyncManager] = None) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>Papers index – {html.escape(root_dir.name)}</title>",
        f"<style>{CSS}</style><script>{JS}</script>",
        "</head><body>",
        f"<h1>Papers index</h1>",
    ]
    
    # Add sync banner if sync is enabled
    if sync_manager:
        parts.append("<div id='sync-banner' class='sync-banner' style='display:block;'>")
        parts.append("<div class='sync-controls'>")
        parts.append("<span id='sync-status' class='sync-status'>Initializing...</span>")
        parts.append("<button id='sync-auth-btn' class='sync-btn' style='display:none;'>Authenticate</button>")
        parts.append("<button id='sync-push-btn' class='sync-btn' style='display:inline-block;'>Push</button>")
        parts.append("</div>")
        parts.append("</div>")
    
    parts.extend([
        "<div class='global-controls'>",
        "<button id='expand-all' class='global-btn' type='button'>Expand all</button>",
        "<button id='collapse-all' class='global-btn' type='button'>Collapse all</button>",
        "</div>",
        f"<div class='folder-path'><strong>Root:</strong> <code>{html.escape(str(root_dir))}</code></div>",
        f"<p>Generated at <time>{html.escape(now)}</time>.</p>",
    ])
    # Skip displaying the artificial root name; start from its children
    for name in sorted(root.children.keys()):
        parts.append(render_node(root.children[name], depth=2, root_dir=root_dir, resolver=resolver))
    parts.append("<footer>Served locally. Click the PDF icon to open the file in a new tab.</footer>")
    parts.append("</body></html>")
    return "\n".join(parts)

def render_node(node: TreeNode, depth: int, root_dir: Path, resolver: PdfResolver) -> str:
    htag = f"h{min(max(depth,1),6)}"
    safe_name = html.escape(node.name)
    # sanitize id: replace non-alnum with '_'
    id_attr = re.sub(r"[^A-Za-z0-9_-]", "_", node.rel_path.as_posix())
    # start collapsed by default
    out: List[str] = [f"<section id='{id_attr}' class='section collapsed'>", "<div class='section-header'>",
                      f"<button class='toggle-btn' aria-expanded='false' aria-controls='{id_attr}-body' title='Collapse/expand'>\u25B6</button>",
                      f"<{htag}>{safe_name}</{htag}>", "</div>", f"<div class='section-body' id='{id_attr}-body'>"]
    if node.entries:
        out.append(render_table_for_entries(node, root_dir, resolver))
    # Recurse children
    for child_name in sorted(node.children.keys()):
        out.append(render_node(node.children[child_name], depth=depth+1, root_dir=root_dir, resolver=resolver))
    out.append("</div>")
    out.append("</section>")
    return "\n".join(out)

def render_table_for_entries(node: TreeNode, root_dir: Path, resolver: PdfResolver) -> str:
    rows: List[str] = []
    for e in node.entries:
        year = html.escape(e.year or "")
        label = html.escape(e.key or "")
        authors = html.escape(e.authors or "")
        title_txt = html.escape(e.title or "")
        # Try resolve pdf path
        pdf_path = resolver.resolve(e)
        pdf_link_html = ""
        if pdf_path is not None:
            try:
                rel = pdf_path.resolve().relative_to(root_dir.resolve())
                url = "/" + quote(rel.as_posix())
                pdf_link_html = f"<a class='pdf' href='{url}' target='_blank' rel='noopener' title='Open PDF'>{PDF_SVG}</a>"
            except Exception:
                pdf_link_html = ""  # outside root_dir -> don't link

        title_cell = f"<span class='title'>{title_txt}</span>{pdf_link_html}"
        rows.append(
            "<tr>"
            f"<td>{year}</td>"
            f"<td><small class='mono'>{label}</small></td>"
            f"<td>{authors}</td>"
            f"<td class='title-cell'>{title_cell}</td>"
            "</tr>"
        )

    table = [
        "<table>",
        "<thead><tr><th>Year</th><th>bibtex_label</th><th>Authors</th><th>Title</th></tr></thead>",
        "<tbody>",
        *rows,
        "</tbody>",
        "</table>",
    ]
    return "\n".join(table)

# --------------------------- HTTP server ---------------------------

class PapersHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: Optional[str] = None, server_data=None, **kwargs):
        self.server_data = server_data  # dict with 'root', 'root_dir', 'resolver', 'sync_manager'
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_index()
        elif self.path == "/sync/status":
            self._serve_sync_status()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/sync/auth":
            self._handle_sync_auth()
        elif self.path == "/sync/pull":
            self._handle_sync_pull()
        elif self.path == "/sync/push":
            self._handle_sync_push()
        else:
            self.send_error(404, "Not found")

    def _serve_index(self):
        root: TreeNode = self.server_data["root"]
        root_dir: Path = self.server_data["root_dir"]
        resolver: PdfResolver = self.server_data["resolver"]
        sync_manager = self.server_data.get("sync_manager")
        html_doc = render_html(root, root_dir, resolver, sync_manager).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_doc)))
        self.end_headers()
        self.wfile.write(html_doc)

    def _serve_sync_status(self):
        """Serve sync status as JSON."""
        try:
            sync_manager = self.server_data.get("sync_manager")
            if not sync_manager:
                status = {"error": "Sync not configured"}
            else:
                status = sync_manager.get_status()
            response = json.dumps(status).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            try:
                self.wfile.write(response)
            except (BrokenPipeError, ConnectionResetError, OSError):
                # Client disconnected before response was sent - ignore
                pass
        except Exception as e:
            # Log error but don't crash
            try:
                error_response = json.dumps({"error": "Internal server error"}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(error_response)))
                self.end_headers()
                self.wfile.write(error_response)
            except:
                pass

    def _handle_sync_auth(self):
        """Handle sync authentication request."""
        sync_manager = self.server_data.get("sync_manager")
        if not sync_manager:
            self.send_error(400, "Sync not configured")
            return

        # Ensure config exists
        if not sync_manager.ensure_rclone_config():
            self.send_error(500, "Failed to create rclone config")
            return

        # Start authorization in a separate thread
        def run_auth():
            try:
                sync_manager._emit_status("auth_running", "Starting authentication...")
                
                # Run authorize which will extract URL, open browser, and wait for completion
                success = sync_manager.run_authorize_with_browser()
                
                if success:
                    # Check if remote is now configured
                    if sync_manager.check_remote_configured():
                        sync_manager._emit_status("done", "Authentication completed successfully")
                    else:
                        sync_manager._emit_status("error", "Authentication completed but remote not configured")
                else:
                    sync_manager._emit_status("error", "Authentication failed")
                    
            except Exception as e:
                sync_manager._emit_status("error", f"Authentication failed: {e}")

        thread = threading.Thread(target=run_auth, daemon=True)
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(b'{"status": "started"}')
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _handle_sync_pull(self):
        """Handle sync pull request."""
        sync_manager = self.server_data.get("sync_manager")
        if not sync_manager:
            self.send_error(400, "Sync not configured")
            return

        def run_pull():
            sync_manager.pull()

        thread = threading.Thread(target=run_pull, daemon=True)
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(b'{"status": "started"}')
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _handle_sync_push(self):
        """Handle sync push request."""
        sync_manager = self.server_data.get("sync_manager")
        if not sync_manager:
            self.send_error(400, "Sync not configured")
            return

        def run_push():
            sync_manager.push()

        thread = threading.Thread(target=run_push, daemon=True)
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(b'{"status": "started"}')
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

# --------------------------- Main ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Serve a papers index from BibTeX files.")
    ap.add_argument("config", help="Path to JSON config file")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    root_node, root_dir, papers_dir, bib_name = build_tree_from_config(cfg)
    resolver = PdfResolver(root_dir=root_dir, papers_dir=papers_dir)

    port = int(cfg.get("papers_port", 8080))

    # Initialize sync manager if enabled
    sync_manager = None
    sync_cfg = cfg.get("sync", {})
    if sync_cfg.get("enabled", False) and SyncManager:
        try:
            sync_manager = SyncManager(config=cfg, root_dir=root_dir)
            
            # Startup sync steps
            print("Initializing sync...")
            
            # Ensure rclone config file exists
            if not sync_manager.ensure_rclone_config():
                print("WARNING: Failed to create rclone config file", file=sys.stderr)
                sync_manager._emit_status("error", "Failed to create rclone config")
            elif not sync_manager.check_rclone_available():
                print("WARNING: rclone binary not found or not available", file=sys.stderr)
                sync_manager._emit_status("error", "rclone binary not found")
            elif not sync_manager.is_sync_ready():
                print("Sync not ready: authentication required")
                sync_manager._emit_status("auth_needed", "Authentication required")
            else:
                # Ensure remote folder exists
                if sync_manager.ensure_remote_folder():
                    # Start file watcher
                    sync_manager.start_watcher_or_scanner()
                    
                    # Pull on start if configured
                    if sync_cfg.get("pull_on_start", False):
                        print("Pulling files from remote...")
                        sync_manager.pull()
                    
                    print("Sync initialized successfully")
                else:
                    print("WARNING: Failed to ensure remote folder exists", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Failed to initialize sync: {e}", file=sys.stderr)
            sync_manager = None

    # Create handler bound to root_dir for static files and with our data attached
    server_data = {
        "root": root_node,
        "root_dir": root_dir,
        "resolver": resolver,
    }
    if sync_manager:
        server_data["sync_manager"] = sync_manager

    Handler = partial(PapersHandler, directory=str(root_dir), server_data=server_data)

    httpd = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving papers index on http://127.0.0.1:{port}  (root_dir={root_dir})")
    print(f"- Bibliography filename: {bib_name}")
    print(f"- Papers dir:           {papers_dir}")
    if sync_manager:
        print(f"- Sync:                 enabled")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        if sync_manager:
            sync_manager.stop_watcher()

if __name__ == "__main__":
    main()
