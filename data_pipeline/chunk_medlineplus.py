"""Split cleaned MedlinePlus definitions into traceable, non-overlapping chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/MedLineGlossary/medlineplus_cleaned.jsonl"
DEFAULT_OUTPUT = ROOT / "data/MedLineGlossary/medlineplus_chunks_800.jsonl"
MAX_CHARS = 800
CHUNK_RULE = "sentence_then_word_800_v1"


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Prefer sentence boundaries, fall back to words, and preserve every character."""
    if not text or text != " ".join(text.split()):
        raise ValueError("Expected nonempty text with normalized whitespace")
    if max_chars < 2:
        raise ValueError("max_chars must be at least 2")

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        window = remaining[: max_chars + 1]
        sentence_ends = [
            match.start() + 1
            for match in re.finditer(r"[.!?] ", window)
            if match.start() + 1 >= max_chars // 2
        ]
        boundary = sentence_ends[-1] if sentence_ends else window.rfind(" ")
        if boundary <= 0:
            raise ValueError("A word exceeds the chunk size; inspect the source text")
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary + 1 :]
    chunks.append(remaining)

    if not all(chunks) or any(len(chunk) > max_chars for chunk in chunks):
        raise AssertionError("Chunk length or content validation failed")
    if " ".join(chunks) != text:
        raise AssertionError("Chunking did not preserve the cleaned definition")
    return chunks


def chunk_file(source: Path, destination: Path, max_chars: int = MAX_CHARS) -> dict[str, int]:
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")
    topics = 0
    split_topics = 0
    chunks = 0
    seen_ids: set[str] = set()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open(encoding="utf-8") as input_file, destination.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_file:
        for line_number, line in enumerate(input_file, 1):
            if not line.strip():
                continue
            topic = json.loads(line)
            for field in ("medical_term", "definition", "source_id", "source_url"):
                if not isinstance(topic.get(field), str) or not topic[field].strip():
                    raise ValueError(f"Line {line_number}: missing {field}")
            if topic.get("source") != "MedlinePlus":
                raise ValueError(f"Line {line_number}: expected MedlinePlus source")
            source_id = topic["source_id"]
            if source_id in seen_ids:
                raise ValueError(f"Line {line_number}: duplicate source_id {source_id}")
            seen_ids.add(source_id)

            pieces = split_text(topic["definition"], max_chars)
            topics += 1
            split_topics += len(pieces) > 1
            for chunk_index, piece in enumerate(pieces):
                chunk_id = hashlib.sha256(
                    f"{source_id}\0{chunk_index}\0{piece}".encode("utf-8")
                ).hexdigest()
                record = {
                    "id": chunk_id,
                    "text": piece,
                    "medical_term": topic["medical_term"],
                    "source": "MedlinePlus",
                    "source_id": source_id,
                    "source_url": topic["source_url"],
                    "chunk_index": chunk_index,
                    "chunk_count": len(pieces),
                }
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                chunks += 1
    return {"topics": topics, "split_topics": split_topics, "chunks": chunks, "max_chars": max_chars}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps({"output": str(args.output), **chunk_file(args.input, args.output)}, indent=2))


if __name__ == "__main__":
    main()
