"""Export cleaned MedlinePlus topics before chunking or embedding.

Uses the same text cleaning, minimum length, and term deduplication rules as
MedlinePlus_EDA.ipynb while retaining the XML source ID and URL for provenance.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/MedLineGlossary/mplus_topics_2026-09-23.xml"
DEFAULT_OUTPUT = ROOT / "data/MedLineGlossary/medlineplus_cleaned.jsonl"


def clean_text(text: str) -> str:
    """Match Ruhma's notebook cleanup for titles and XML summary text."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def export_cleaned(source: Path, destination: Path) -> dict[str, int]:
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")

    root = ET.parse(source).getroot()
    topics = root.findall(".//health-topic")
    cleaned = []
    seen_terms: set[str] = set()
    short_or_empty = 0
    duplicates = 0

    for topic in topics:
        term = clean_text(topic.get("title", ""))
        summary = topic.find(".//full-summary")
        definition = clean_text("".join(summary.itertext()) if summary is not None else "")

        # Ruhma's EDA keeps definitions longer than 15 characters, then keeps
        # the first occurrence of each Medical_Term.
        if len(definition) <= 15:
            short_or_empty += 1
            continue
        if term in seen_terms:
            duplicates += 1
            continue
        seen_terms.add(term)

        cleaned.append(
            {
                "medical_term": term,
                "definition": definition,
                "source": "MedlinePlus",
                "source_id": topic.get("id", ""),
                "source_url": topic.get("url", ""),
            }
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as output:
        for record in cleaned:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "original_topics": len(topics),
        "removed_empty_or_short": short_or_empty,
        "after_length_filter": len(topics) - short_or_empty,
        "removed_duplicate_terms": duplicates,
        "cleaned_topics": len(cleaned),
        "missing_source_ids": sum(not row["source_id"] for row in cleaned),
        "missing_source_urls": sum(not row["source_url"] for row in cleaned),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = export_cleaned(args.input, args.output)
    print(json.dumps({"output": str(args.output), **report}, indent=2))


if __name__ == "__main__":
    main()
