"""Run the single-Gemini baseline with the current MedlinePlus MiniLM index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from baseline import BaselineInput, GeminiGenerator, run_baseline
from retrieval.gemini_chroma import api_key
from retrieval.minilm_chroma import (
    COLLECTION as RETRIEVAL_COLLECTION,
    DB_PATH,
    MODEL as RETRIEVAL_MODEL,
    MiniLMTextQueryCollection,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON file with one BaselineInput")
    parser.add_argument("--output", type=Path, required=True, help="Where to save the JSON result")
    parser.add_argument("--model", required=True, help="Explicit Gemini text-generation model ID")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    example = BaselineInput(**payload)
    collection = MiniLMTextQueryCollection(args.db)

    from google import genai

    with genai.Client(api_key=api_key()) as client:
        result = run_baseline(
            example,
            collection=collection,
            generator=GeminiGenerator(client, model=args.model),
            top_k=args.top_k,
        )

    result["retrieval_index"] = {
        "collection": RETRIEVAL_COLLECTION,
        "embedding_model": RETRIEVAL_MODEL,
        "source_sha256": collection.target.metadata.get("source_sha256"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {result['status']} result to {args.output}")


if __name__ == "__main__":
    main()
