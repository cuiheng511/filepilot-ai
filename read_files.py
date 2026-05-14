#!/usr/bin/env python
"""Read all panel files and print their content."""

import os

base = os.path.join(os.path.dirname(__file__), "filepilot", "ui")
files = [
    "main_window.py",
    "index_panel.py",
    "organize_panel.py",
    "duplicates_panel.py",
    "summary_panel.py",
    "file_browser.py",
    "search_panel.py",
]

for fname in files:
    fpath = os.path.join(base, fname)
    print(f"===== {fname} =====")
    with open(fpath, encoding="utf-8") as f:
        print(f.read())
    print()
