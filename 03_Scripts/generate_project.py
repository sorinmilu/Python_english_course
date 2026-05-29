import os
import re
import sys
import json
import hashlib
import subprocess
import argparse
from string import Template
import shutil

from program_utils import parse_program_token, render_program

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def shorten_path(path, root_dir):
    """Return a path relative to root_dir for concise printing. If that fails, return the normalized path."""
    try:
        return os.path.relpath(path, root_dir).replace('\\', '/')
    except Exception:
        return os.path.normpath(path).replace('\\', '/')


_VERBATIM_BLOCK_RE = re.compile(
    r'\\begin\{(?:verbatim|minted|lstlisting|codebox)\}.*?\\end\{(?:verbatim|minted|lstlisting|codebox)\}',
    re.DOTALL,
)
_LATEX_QUOTE_RE = re.compile(r"``((?:[^']|'(?![']))*?)''")
_MARKDOWN_BACKTICK_RE = re.compile(r'(?<!`)`([^`\n]+)`(?!`)')


def _protect_latex_quotes(tex):
    """Temporarily replace LaTeX ``...'' quotes so backtick conversion cannot span them."""
    quotes = []

    def repl(match):
        quotes.append(match.group(0))
        return f"\x00LATEXQUOTE{len(quotes) - 1}\x00"

    return _LATEX_QUOTE_RE.sub(repl, tex), quotes


def _restore_latex_quotes(tex, quotes):
    for i, quote in enumerate(quotes):
        tex = tex.replace(f"\x00LATEXQUOTE{i}\x00", quote)
    return tex


def _escape_texttt(text):
    """Escape characters that are special inside \\texttt{...}."""
    replacements = (
        ('\\', r'\textbackslash{}'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('#', r'\#'),
        ('$', r'\$'),
        ('%', r'\%'),
        ('&', r'\&'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _convert_backticks_in_segment(tex):
    tex, quotes = _protect_latex_quotes(tex)

    def repl(match):
        return r'\texttt{' + _escape_texttt(match.group(1)) + '}'

    tex = _MARKDOWN_BACKTICK_RE.sub(repl, tex)
    return _restore_latex_quotes(tex, quotes)


def convert_markdown_backticks(tex):
    """Turn markdown-style `identifiers` into LaTeX \\texttt{...} outside verbatim blocks."""
    parts = []
    last = 0
    for match in _VERBATIM_BLOCK_RE.finditer(tex):
        parts.append(_convert_backticks_in_segment(tex[last:match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_convert_backticks_in_segment(tex[last:]))
    return ''.join(parts)


def extract_headings(tex_content):
    """Extract \chapter, \section, \subsection and \subsubsection headings and their adjacent labels from a LaTeX string.

    Returns a list of tuples: (level, title, label_or_No_label)
    """
    headings = []
    # find chapter, section, subsection, subsubsection
    pattern = re.compile(r'\\(chapter|section|subsection|subsubsection)\s*\{([^}]+)\}', re.MULTILINE)
    for m in pattern.finditer(tex_content):
        level = m.group(1)
        title = m.group(2).strip()
        # look for a \label{...} immediately after the heading (within next 300 chars)
        start = m.end()
        look = tex_content[start:start+300]
        lab = re.search(r'\\label\{([^}]+)\}', look)
        label = lab.group(1) if lab else 'No label'
        headings.append((level, title, label))
    return headings


def write_headings_md(headings, out_path):
    """Write extracted headings to a markdown file at out_path."""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('# Document Headings\n\n')
        for level, title, label in headings:
            if level == 'chapter':
                f.write(f'## {title}\n')
                f.write(f'Label: {label}\n\n')
            elif level == 'section':
                f.write(f'### {title}\n')
                f.write(f'Label: {label}\n\n')
            elif level == 'subsection':
                f.write(f'#### {title}\n')
                f.write(f'Label: {label}\n\n')
            elif level == 'subsubsection':
                f.write(f'##### {title}\n')
                f.write(f'Label: {label}\n\n')


def extract_figures(tex_content, root_dir, temp_dir):
    """Extract figures from LaTeX content.

    Returns list of dicts with keys: chapter, section, subsection, label, caption, path, exists
    """
    figures = []
    # Patterns
    heading_pat = re.compile(r'\\(chapter|section|subsection)\s*\{([^}]+)\}', re.MULTILINE)
    fig_env_pat = re.compile(r'\\begin\{figure[^}]*\}(.+?)\\end\{figure\}', re.DOTALL)
    include_pat = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}')
    caption_pat = re.compile(r'\\caption\s*\{([^}]+)\}')
    label_pat = re.compile(r'\\label\s*\{([^}]+)\}')

    # Walk through document, tracking current headings
    current = {'chapter': None, 'section': None, 'subsection': None}
    pos = 0
    # iterate through headings and figure environments in order
    combined_pat = re.compile(r'\\begin\{figure|\\(chapter|section|subsection)\s*\{', re.MULTILINE)
    for m in combined_pat.finditer(tex_content):
        token = m.group(0)
        if token.startswith('\\begin{figure'):
            # find the full figure environment from this position
            fm = fig_env_pat.search(tex_content, m.start())
            if not fm:
                continue
            block = fm.group(1)
            # find includegraphics
            inc = include_pat.search(block)
            path = inc.group(1).strip() if inc else None
            capm = caption_pat.search(block)
            caption = capm.group(1).strip() if capm else 'No caption'
            labm = label_pat.search(block)
            label = labm.group(1).strip() if labm else 'No label'
            # resolve path existence
            exists = False
            resolved = None
            if path:
                # try absolute
                if os.path.isabs(path) and os.path.exists(path):
                    exists = True
                    resolved = path
                else:
                    # try relative to root_dir
                    p1 = os.path.join(root_dir, path)
                    p2 = os.path.join(temp_dir, path)
                    if os.path.exists(p1):
                        exists = True
                        resolved = p1
                    elif os.path.exists(p2):
                        exists = True
                        resolved = p2
                    else:
                        # try as provided (maybe already absolute normalized)
                        if os.path.exists(path):
                            exists = True
                            resolved = path
            figures.append({
                'chapter': current['chapter'],
                'section': current['section'],
                'subsection': current['subsection'],
                'label': label,
                'caption': caption,
                'path': path,
                'exists': exists,
                'resolved': resolved,
            })
            pos = fm.end()
        else:
            # heading
            # match heading at m.start()
            hm = heading_pat.match(tex_content, m.start())
            if hm:
                lvl = hm.group(1)
                title = hm.group(2).strip()
                if lvl == 'chapter':
                    current['chapter'] = title
                    current['section'] = None
                    current['subsection'] = None
                elif lvl == 'section':
                    current['section'] = title
                    current['subsection'] = None
                elif lvl == 'subsection':
                    current['subsection'] = title
                pos = hm.end()

    # Additionally, catch standalone includegraphics outside figure envs
    for im in include_pat.finditer(tex_content):
        # check if this include was already captured by fig env scan
        inc_start = im.start()
        # skip if inside any recorded figure (approx check by searching nearby caption/label)
        near_label = label_pat.search(tex_content, inc_start-200, inc_start+200)
        near_caption = caption_pat.search(tex_content, inc_start-200, inc_start+200)
        # find nearest preceding heading for position
        prev_headings = list(heading_pat.finditer(tex_content, 0, inc_start))
        current = {'chapter': None, 'section': None, 'subsection': None}
        if prev_headings:
            for ph in prev_headings:
                lvl = ph.group(1)
                title = ph.group(2).strip()
                if lvl == 'chapter':
                    current['chapter'] = title
                    current['section'] = None
                    current['subsection'] = None
                elif lvl == 'section':
                    current['section'] = title
                    current['subsection'] = None
                elif lvl == 'subsection':
                    current['subsection'] = title
        path = im.group(1).strip()
        caption = near_caption.group(1).strip() if near_caption else 'No caption'
        label = near_label.group(1).strip() if near_label else 'No label'
        # check existence
        exists = False
        resolved = None
        if path:
            if os.path.isabs(path) and os.path.exists(path):
                exists = True
                resolved = path
            else:
                p1 = os.path.join(root_dir, path)
                p2 = os.path.join(temp_dir, path)
                if os.path.exists(p1):
                    exists = True
                    resolved = p1
                elif os.path.exists(p2):
                    exists = True
                    resolved = p2
                elif os.path.exists(path):
                    exists = True
                    resolved = path
        figures.append({
            'chapter': current['chapter'],
            'section': current['section'],
            'subsection': current['subsection'],
            'label': label,
            'caption': caption,
            'path': path,
            'exists': exists,
            'resolved': resolved,
        })

    return figures


def write_list_of_figures_md(figures, out_path, root_dir):
    """Write list_of_figures.md grouped by chapter/section/subsection."""
    # organize
    tree = {}
    for fig in figures:
        ch = fig['chapter'] or 'No Chapter'
        sec = fig['section'] or 'No Section'
        sub = fig['subsection'] or 'No Subsection'
        tree.setdefault(ch, {}).setdefault(sec, {}).setdefault(sub, []).append(fig)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('# List of Figures\n\n')
        for ch, secs in tree.items():
            f.write(f'## {ch}\n\n')
            for sec, subs in secs.items():
                f.write(f'### {sec}\n\n')
                for sub, figs in subs.items():
                    f.write(f'#### {sub}\n\n')
                    for fig in figs:
                        label = fig.get('label', 'No label')
                        caption = fig.get('caption', 'No caption')
                        path = fig.get('path') or 'No path'
                        exists = 'Yes' if fig.get('exists') else 'No'
                        # make path shorter for display
                        display_path = shorten_path(fig.get('resolved') or path, root_dir)
                        f.write(f'- **Label:** {label}  \n')
                        f.write(f'  **Caption:** {caption}  \n')
                        f.write(f'  **File:** {display_path}  \n')
                        f.write(f'  **Exists:** {exists}  \n\n')

def file_checksum(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def files_differ(src, dst):
    """Return True if files differ (by checksum) or dst missing."""
    if not os.path.exists(dst):
        return True
    try:
        return file_checksum(src) != file_checksum(dst)
    except Exception:
        # if any error comparing, assume different
        return True


def sync_directory(source_dir, dest_dir, root_dir=None):
    """Recursively copy files from source_dir into dest_dir.

    Only copies files that are missing or differ. Directories are created as needed.
    Paths are preserved relative to source_dir when copied into dest_dir.
    """
    if not os.path.isdir(source_dir):
        return []
    copied = []
    for dirpath, dirnames, filenames in os.walk(source_dir):
        rel_dir = os.path.relpath(dirpath, source_dir)
        if rel_dir == '.':
            rel_dir = ''
        for fname in filenames:
            src_path = os.path.join(dirpath, fname)
            rel_path = os.path.join(rel_dir, fname) if rel_dir else fname
            dst_path = os.path.join(dest_dir, rel_path)
            dst_folder = os.path.dirname(dst_path)
            ensure_dir(dst_folder)
            try:
                if files_differ(src_path, dst_path):
                    shutil.copy2(src_path, dst_path)
                    copied.append((src_path, dst_path))
            except Exception:
                # best-effort: try a straight copy if checksum failed
                try:
                    shutil.copy2(src_path, dst_path)
                    copied.append((src_path, dst_path))
                except Exception:
                    pass
    # Optionally print summary relative to root_dir
    if root_dir:
        for s, d in copied:
            print(f"Copied: {os.path.relpath(s, root_dir).replace('\\', '/')} -> {os.path.relpath(d, root_dir).replace('\\', '/')}")
    else:
        for s, d in copied:
            print(f"Copied: {s} -> {d}")
    return copied

def load_templates(root_dir, templates_folder, template_files):
    templates_path = os.path.join(root_dir, templates_folder)
    loaded = {}
    for key, filename in template_files.items():
        full_path = os.path.join(templates_path, filename)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Template file '{filename}' not found in {templates_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            loaded[key] = Template(f.read())
    return loaded

def cached_asset_path(source_file, root_dir, temp_dir):
    rel_path = os.path.relpath(source_file, root_dir)
    base, ext = os.path.splitext(rel_path)
    ext_out = '.png' if ext.lower() == '.puml' else ext
    asset_path = os.path.join(temp_dir, base + ext_out)
    asset_dir = os.path.dirname(asset_path)
    ensure_dir(asset_dir)
    return asset_path

def is_asset_up_to_date(source_file, asset_file):
    meta_file = asset_file + ".meta"
    if not os.path.exists(asset_file) or not os.path.exists(meta_file):
        return False
    try:
        with open(meta_file, 'r') as f:
            stored_checksum = f.read().strip()
    except Exception:
        return False
    current_checksum = file_checksum(source_file)
    return stored_checksum == current_checksum

def update_asset_checksum(source_file, asset_file):
    meta_file = asset_file + ".meta"
    checksum = file_checksum(source_file)
    with open(meta_file, 'w') as f:
        f.write(checksum)

def process_puml(source_file, root_dir, temp_dir, templates, opts=None):
    asset_file = cached_asset_path(source_file, root_dir, temp_dir)
    if is_asset_up_to_date(source_file, asset_file):
        # asset up-to-date; still report external image
        pass
    else:
        # regenerate PlantUML diagram
        cwd = os.path.dirname(source_file)
        basename = os.path.splitext(os.path.basename(source_file))[0]
        ensure_dir(os.path.dirname(asset_file))
        # Call plantuml CLI (assumes plantuml installed and in PATH)
        subprocess.run(['plantuml', '-tpng', basename + '.puml'], cwd=cwd, check=True)
        generated_file = os.path.join(cwd, basename + '.png')
        if os.path.exists(generated_file):
            os.replace(generated_file, asset_file)
            update_asset_checksum(source_file, asset_file)
        else:
            raise FileNotFoundError(f"Expected PlantUML output {generated_file} not found.")
    rel_asset_path = os.path.relpath(asset_file, root_dir).replace('\\', '/')
    caption = f"Diagram generated from {os.path.basename(source_file)}"
    # report external image produced/used
    print(f"External image: {rel_asset_path}")
    return templates['figure_template'].substitute(path=rel_asset_path, caption=caption)

def process_tex(source_file, root_dir, temp_dir, templates, opts=None):
    rel_path = os.path.relpath(source_file, root_dir).replace('\\', '/')
    print(f"Processed LaTeX file: {rel_path}")
    # Inline the contents of the .tex file (behave like .tikz/.pgfp)
    with open(source_file, 'r', encoding='utf-8') as f:
        tex_code = f.read()
    return convert_markdown_backticks(tex_code)

def process_image(source_file, root_dir, temp_dir, templates, opts=None):
    if not os.path.isfile(source_file):
        raise FileNotFoundError(f"Image file not found: {shorten_path(source_file, root_dir)}")

    abs_path = os.path.abspath(source_file).replace('\\', '/')  # absolute path with forward slashes
    caption = f"Image {os.path.basename(source_file)}"
    # Determine width: default kept at 0.8\textwidth unless overridden by opts['width_factor']
    default_width = '0.8\\textwidth'
    width = default_width
    if opts and isinstance(opts, dict):
        wf = opts.get('width_factor')
        if wf:
            width = f"{wf}\\textwidth"

    # print path relative to root_dir for brevity
    print(f"External image: {shorten_path(source_file, root_dir)}")
    return templates['image_template'].substitute(path=abs_path, caption=caption, width=width)

def dispatcher(filepath, root_dir, temp_dir, templates, opts=None):
    ext = os.path.splitext(filepath)[1].lower()
    full_path = os.path.join(root_dir, filepath)
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"Referenced file not found: {shorten_path(full_path, root_dir)}")
    if ext == ".puml":
        return process_puml(full_path, root_dir, temp_dir, templates, opts=opts)
    elif ext == ".tex":
        return process_tex(full_path, root_dir, temp_dir, templates, opts=opts)
    elif ext in [".png", ".jpg", ".jpeg", ".pdf"]:
        return process_image(full_path, root_dir, temp_dir, templates, opts=opts)
    elif ext == ".pgfp":
        return process_pgfp(full_path, root_dir, temp_dir, templates, opts=opts)
    elif ext == ".tikz":
        return process_tikz(full_path, root_dir, temp_dir, templates, opts=opts)

    else:
        raise ValueError(f"Unsupported file extension for file {filepath}")

def process_program(program_rel_path, content_dir, root_dir, templates, opts=None):
    full_path = os.path.normpath(os.path.join(content_dir, program_rel_path))
    if not os.path.isdir(full_path):
        raise FileNotFoundError(
            f"Program directory not found: {shorten_path(full_path, root_dir)}"
        )
    rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
    print(f"Processed program: {rel_path}")
    return render_program(full_path, templates, opts or {})


def process_content_file(content_path, root_dir, temp_dir, templates):
    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    content_dir = os.path.dirname(content_path)

    program_pattern = re.compile(r'%<<<PROGRAM:(.+?)>>>')

    def program_replacer(match):
        token = match.group(1).strip()
        rel_path, overrides = parse_program_token(token)
        return process_program(rel_path, content_dir, root_dir, templates, opts=overrides)

    content = program_pattern.sub(program_replacer, content)

    placeholder_pattern = re.compile(r'%<<<INCLUDE:(.+?)>>>')

    def replacer(match):
        token = match.group(1).strip()
        # Support optional pipe parameter like: path|0.8  (meaning 0.8\textwidth)
        if '|' in token:
            parts = token.split('|', 1)
            rel_path = parts[0].strip()
            param = parts[1].strip()
        else:
            rel_path = token
            param = None

        full_rel_path = os.path.normpath(os.path.join(content_dir, rel_path))

        opts = {}
        if param:
            # accept a single numeric factor like 0.8 meaning fraction of \textwidth
            m = re.match(r'^([0-9]*\.?[0-9]+)$', param)
            if m:
                opts['width_factor'] = m.group(1)
            else:
                # ignore unrecognized parameter silently
                pass

        return dispatcher(full_rel_path, root_dir, temp_dir, templates, opts=opts if opts else None)

    processed = placeholder_pattern.sub(replacer, content)
    return convert_markdown_backticks(processed)

def process_tikz(full_path, root_dir, temp_dir, templates, opts=None):
    rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
    print(f"Processed LaTeX file: {rel_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        tikz_code = f.read()
    return tikz_code

def process_pgfp(full_path, root_dir, temp_dir, templates, opts=None):
    rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
    print(f"Processed LaTeX file: {rel_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        pgfp_code = f.read()
    return pgfp_code


def merge_all_contents(temp_dir, inspected_folders):
    merged_content = []
    for folder in inspected_folders:
        processed_path = os.path.join(temp_dir, folder, "content_processed.tex")
        if os.path.isfile(processed_path):
            with open(processed_path, "r", encoding="utf-8") as f:
                merged_content.append(f.read())
        else:
            # silently skip folders without processed content
            pass
    return "\n\n".join(merged_content)

def process_main_document(root_dir, latex_root, main_latex_file, temp_dir, merged_content, main_placeholder):
    main_doc_path = os.path.join(root_dir, latex_root, main_latex_file)
    if not os.path.isfile(main_doc_path):
        print(f"Main LaTeX file not found: {shorten_path(main_doc_path, root_dir)}")
        sys.exit(1)

    with open(main_doc_path, "r", encoding="utf-8") as f:
        main_doc_content = f.read()

    if main_placeholder not in main_doc_content:
        # placeholder missing; proceed without printing
        pass

    final_content = main_doc_content.replace(main_placeholder, merged_content)

    output_main_path = os.path.join(temp_dir, main_latex_file.replace(".tex", "_processed.tex"))
    with open(output_main_path, "w", encoding="utf-8") as outf:
        outf.write(final_content)
    print(f"Processed LaTeX file: {os.path.relpath(output_main_path, root_dir).replace('\\\\', '/')}")



def merge_bib_files(inspected_dirs, root_dir, bibliography_file, output_bib_path):
    """
    Merge multiple bibliography files from inspected_dirs into a single .bib file.
    Deduplicate entries by citation key.
    Insert LaTeX-style comments with the source file name before each group of entries.
    """
    entries = {}
    bib_entry_pattern = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)

    merged_output = []

    for dir_rel in inspected_dirs:
        bib_path = os.path.join(root_dir, dir_rel, bibliography_file)
        if os.path.isfile(bib_path):
            with open(bib_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add comment with source file name
            merged_output.append(f"% Entries extracted from {os.path.relpath(bib_path, root_dir)}\n")

            # Split content into entries by '@'
            raw_entries = content.split('@')[1:]  # skip header before first '@'

            for raw_entry in raw_entries:
                raw_entry = '@' + raw_entry.strip()
                match = bib_entry_pattern.match(raw_entry)
                if not match:
                    continue
                citation_key = match.group(2)

                if citation_key in entries:
                    # If duplicate, skip silently (or warn if desired)
                    continue
                entries[citation_key] = raw_entry
                merged_output.append(raw_entry + "\n\n")

    # Write merged bibliography file
    with open(output_bib_path, 'w', encoding='utf-8') as out_file:
        out_file.writelines(merged_output)
    # do not print here; keep output focused on LaTeX files and external images



def main():
    parser = argparse.ArgumentParser(description="Process LaTeX content files replacing placeholders with generated LaTeX code.")
    parser.add_argument("config", help="Path to JSON configuration file")
    args = parser.parse_args()

    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    root_dir = config.get("root_dir")
    inspected_folders = config.get("inspected_folders", [])
    temp_dir = config.get("temp_dir")
    templates_folder = config.get("templates")
    template_files = config.get("template_files", {})
    latex_root = config.get("latex_root")
    main_latex_file = config.get("main_latex_file")
    main_placeholder = config.get("main_placeholder", "%<<<INSERT_CONTENT>>>")
    bibliography_file = config.get("bibliography_file", "references.bib")
    final_bibliography_file = config.get("final_bibliography_file", "full_references.bib")

    if not root_dir or not temp_dir or not templates_folder or not template_files or not isinstance(inspected_folders, list):
        print("Invalid config: must include root_dir (str), temp_dir (str), templates (str), template_files (dict), inspected_folders (list)")
        sys.exit(1)

    if not os.path.isabs(temp_dir):
        temp_dir = os.path.join(root_dir, temp_dir)

    ensure_dir(temp_dir)

    # Load templates once
    templates = load_templates(root_dir, templates_folder, template_files)

    # Process each inspected folder's content.tex
    for folder in inspected_folders:
        content_tex_path = os.path.join(root_dir, folder, "content.tex")
        if os.path.isfile(content_tex_path):
            processed_tex = process_content_file(content_tex_path, root_dir, temp_dir, templates)
            output_folder = os.path.join(temp_dir, folder)
            ensure_dir(output_folder)
            output_path = os.path.join(output_folder, "content_processed.tex")
            with open(output_path, "w", encoding="utf-8") as outf:
                outf.write(processed_tex)
            print(f"Processed LaTeX file: {os.path.relpath(output_path, root_dir).replace('\\', '/')}")
        else:
            # silently skip folders without content.tex
            pass

    # Merge all processed content files
    merged_content = merge_all_contents(temp_dir, inspected_folders)

    # Extract headings (chapters and sections) from merged content and write headings.md
    try:
        headings = extract_headings(merged_content)
        headings_md_path = os.path.join(temp_dir, 'headings.md')
        write_headings_md(headings, headings_md_path)
        print(f"Processed LaTeX file: {os.path.relpath(headings_md_path, root_dir).replace('\\', '/')}")
    except Exception:
        # don't break the run for heading extraction failures
        pass

    # Extract figures and write list_of_figures.md
    try:
        figures = extract_figures(merged_content, root_dir, temp_dir)
        lof_path = os.path.join(temp_dir, 'list_of_figures.md')
        write_list_of_figures_md(figures, lof_path, root_dir)
        print(f"Processed LaTeX file: {os.path.relpath(lof_path, root_dir).replace('\\', '/')}")
    except Exception:
        pass

    # Merge bibliography files into final bibliography file inside latex_root folder
    final_bib_path = os.path.join(root_dir, latex_root, final_bibliography_file)
    ensure_dir(os.path.dirname(final_bib_path))
    merge_bib_files(inspected_folders, root_dir, bibliography_file, final_bib_path)

    # Copy final bibliography file to the build folder (temp_dir)
    if os.path.isfile(final_bib_path):
        dest_bib_path = os.path.join(temp_dir, os.path.basename(final_bibliography_file))
        shutil.copy2(final_bib_path, dest_bib_path)
        # do not print copy actions
    else:
        # silent if missing
        pass

    # Process main LaTeX document with placeholder replaced by merged content
    if not latex_root or not main_latex_file:
        # skipping main document merge silently
        pass
    else:
        process_main_document(root_dir, latex_root, main_latex_file, temp_dir, merged_content, main_placeholder)

    # If configured, copy an auxiliary directory from the latex root into the build folder.
    # The ground truth source is always under `02_latex/<copy_to_build>` (latex_root/<copy_to_build>).
    copy_to_build = config.get("copy_to_build")
    if copy_to_build:
        source_dir = os.path.join(root_dir, latex_root, copy_to_build)
        if os.path.isdir(source_dir):
            # sync source_dir into temp_dir/<copy_to_build> (e.g. build/temp/layers/).
            dest_dir = os.path.join(temp_dir, copy_to_build)
            sync_directory(source_dir, dest_dir, root_dir=root_dir)
        else:
            print(f"Configured copy_to_build directory not found: {os.path.relpath(source_dir, root_dir).replace('\\', '/')}" )



if __name__ == "__main__":
    main()
