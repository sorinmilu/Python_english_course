#!/usr/bin/env python3
import os
import sys

root = os.path.join(os.path.dirname(__file__), "..", "00_CONTENT")
root = os.path.abspath(root)
rows = []
for dp, dns, _fns in os.walk(root):
    for d in dns:
        p = os.path.join(dp, d)
        rel = os.path.relpath(p, root).replace("\\", "/")
        build_path = f"build/temp/00_CONTENT/{rel}/content_processed.tex"
        if len(d) > 35 or len(build_path) > 180:
            rows.append((len(build_path), len(d), rel))
for item in sorted(rows, reverse=True):
    print(item)
print("TOTAL:", len(rows))
