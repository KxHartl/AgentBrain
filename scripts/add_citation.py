#!/usr/bin/env python3
"""
AgentBrain - BibTeX Citation Generator
Automatski dodaje novu BibTeX referencu u docs/references.bib
Korištenje:
  python ~/.agentbrain/scripts/add_citation.py --id "smith2024" --type "article" --title "AI in Robotics" --author "John Smith" --year "2024" --url "http://example.com"
"""

import argparse
import os
from pathlib import Path

def create_bibtex_entry(args):
    entry = f"\n@{args.type}{{{args.id},\n"
    if args.author:
        entry += f"  author = {{{args.author}}},\n"
    if args.title:
        entry += f"  title = {{{args.title}}},\n"
    if args.year:
        entry += f"  year = {{{args.year}}},\n"
    if args.journal:
        entry += f"  journal = {{{args.journal}}},\n"
    if args.publisher:
        entry += f"  publisher = {{{args.publisher}}},\n"
    if args.url:
        entry += f"  url = {{{args.url}}},\n"
    if args.note:
        entry += f"  note = {{{args.note}}},\n"
    entry += "}\n"
    return entry

def main():
    parser = argparse.ArgumentParser(description="Add a BibTeX entry to references.bib")
    parser.add_argument("--id", required=True, help="Citation ID (e.g. smith2024)")
    parser.add_argument("--type", default="misc", help="Entry type (article, book, misc)")
    parser.add_argument("--title", required=True, help="Title of the work")
    parser.add_argument("--author", help="Author(s)")
    parser.add_argument("--year", help="Year of publication")
    parser.add_argument("--journal", help="Journal name")
    parser.add_argument("--publisher", help="Publisher name")
    parser.add_argument("--url", help="URL of the document")
    parser.add_argument("--note", help="Additional notes (e.g., accessed date)")
    
    args = parser.parse_args()
    
    root = Path.cwd()
    docs_dir = root / "docs"
    
    if not docs_dir.exists():
        print("Error: 'docs' directory not found. Please run this from the project root.")
        return

    bib_file = docs_dir / "references.bib"
    
    # Create the file if it doesn't exist
    if not bib_file.exists():
        bib_file.write_text("% Auto-generated BibTeX references\n", encoding="utf-8")
        print("Created new references.bib")

    entry = create_bibtex_entry(args)
    
    with open(bib_file, "a", encoding="utf-8") as f:
        f.write(entry)
        
    print(f"Successfully added citation '{args.id}' to docs/references.bib")

if __name__ == "__main__":
    main()
