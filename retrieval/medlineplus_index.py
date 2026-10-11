"""Shared input validation for the separate MedlinePlus embedding indexes."""

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data/MedLineGlossary/medlineplus_chunks_800.jsonl"
CHUNK_RULE = "sentence_then_word_800_v1"


def source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_chunks(path: Path) -> list[dict[str, Any]]:
    rows = []
    seen_ids: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            for field in ("id", "text", "medical_term", "source_id", "source_url"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f"Line {line_number}: missing {field}")
            if row.get("source") != "MedlinePlus" or len(row["text"]) > 800:
                raise ValueError(f"Line {line_number}: wrong source or oversized chunk")
            if row["id"] in seen_ids:
                raise ValueError(f"Line {line_number}: duplicate chunk ID")
            seen_ids.add(row["id"])
            rows.append(row)
    if not rows:
        raise ValueError("No MedlinePlus chunks found")
    return rows
