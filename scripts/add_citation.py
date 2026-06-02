#!/usr/bin/env python3
"""
AgentBrain - BibTeX Citation Generator
Adds a new BibTeX reference to docs/references.bib.

Usage:
  Manual entry:
    python ~/.agentbrain/scripts/add_citation.py --id "smith2024" --type "article" --title "AI in Robotics" --author "John Smith" --year "2024"

  Auto-fetch from DOI (recommended):
    python ~/.agentbrain/scripts/add_citation.py --doi "10.1109/TRO.2024.1234567"
"""

import argparse
import json
import urllib.request
import urllib.error
from pathlib import Path


def fetch_from_doi(doi: str) -> dict:
    """Fetch citation metadata from CrossRef API using DOI."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "LiteRealm/2.0 (mailto:user@example.com)"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["message"]
    except urllib.error.HTTPError as e:
        print(f"CrossRef API error: {e.code} — check that the DOI is correct.")
        return {}
    except Exception as e:
        print(f"Failed to fetch DOI metadata: {e}")
        return {}

    # Extract authors
    authors = []
    for a in data.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            authors.append(f"{family}, {given}" if given else family)
    author_str = " and ".join(authors)

    # Extract year
    year = ""
    for date_field in ["published-print", "published-online", "issued"]:
        parts = data.get(date_field, {}).get("date-parts", [[]])
        if parts and parts[0] and parts[0][0]:
            year = str(parts[0][0])
            break

    # Generate citation ID
    first_author = data.get("author", [{}])[0].get("family", "unknown").lower()
    cite_id = f"{first_author}{year}"

    # Determine entry type
    entry_type = "article"
    container = data.get("type", "")
    if "book" in container:
        entry_type = "book"
    elif "proceedings" in container:
        entry_type = "inproceedings"

    result = {
        "id": cite_id,
        "type": entry_type,
        "title": data.get("title", [""])[0],
        "author": author_str,
        "year": year,
        "journal": data.get("container-title", [""])[0] if data.get("container-title") else "",
        "publisher": data.get("publisher", ""),
        "doi": doi,
        "url": f"https://doi.org/{doi}",
    }

    return {k: v for k, v in result.items() if v}


def create_bibtex_entry(fields: dict) -> str:
    """Create a BibTeX entry string from a dict of fields."""
    cite_id = fields.pop("id", "unknown")
    entry_type = fields.pop("type", "misc")

    entry = f"\n@{entry_type}{{{cite_id},\n"
    for key, value in fields.items():
        if value:
            entry += f"  {key} = {{{value}}},\n"
    entry += "}\n"
    return entry


def main():
    parser = argparse.ArgumentParser(description="Add a BibTeX entry to references.bib")

    # DOI mode (auto-fetch)
    parser.add_argument("--doi", help="Fetch metadata automatically from DOI")

    # Manual mode
    parser.add_argument("--id", help="Citation ID (e.g. smith2024)")
    parser.add_argument("--type", default="misc", help="Entry type (article, book, misc)")
    parser.add_argument("--title", help="Title of the work")
    parser.add_argument("--author", help="Author(s)")
    parser.add_argument("--year", help="Year of publication")
    parser.add_argument("--journal", help="Journal name")
    parser.add_argument("--publisher", help="Publisher name")
    parser.add_argument("--url", help="URL of the document")
    parser.add_argument("--note", help="Additional notes")

    args = parser.parse_args()

    # Determine fields
    if args.doi:
        print(f"Fetching metadata for DOI: {args.doi}")
        fields = fetch_from_doi(args.doi)
        if not fields:
            print("Could not fetch DOI metadata. Use manual entry instead.")
            return
        print(f"  Found: {fields.get('title', 'unknown')}")
    elif args.id and args.title:
        fields = {
            "id": args.id,
            "type": args.type,
            "title": args.title,
            "author": args.author or "",
            "year": args.year or "",
            "journal": args.journal or "",
            "publisher": args.publisher or "",
            "url": args.url or "",
            "note": args.note or "",
        }
        fields = {k: v for k, v in fields.items() if v}
    else:
        print("Error: Provide either --doi or (--id + --title).")
        parser.print_help()
        return

    # Find bib file
    root = Path.cwd()
    docs_dir = root / "docs"

    if not docs_dir.exists():
        print("Error: 'docs' directory not found. Run this from the project root.")
        return

    bib_file = docs_dir / "references.bib"

    if not bib_file.exists():
        bib_file.write_text("% Auto-generated BibTeX references\n", encoding="utf-8")
        print("Created new references.bib")

    entry = create_bibtex_entry(fields)

    with open(bib_file, "a", encoding="utf-8") as f:
        f.write(entry)

    cite_id = entry.split("{")[1].split(",")[0]
    print(f"Added citation '{cite_id}' to docs/references.bib")


if __name__ == "__main__":
    main()
