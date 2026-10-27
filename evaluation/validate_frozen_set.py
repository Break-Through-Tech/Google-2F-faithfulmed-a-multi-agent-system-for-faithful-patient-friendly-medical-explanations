"""Verify the frozen source inputs and completed source-review annotations."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = ROOT / "data/curated_baseline"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate(directory=DEFAULT_DIRECTORY, source=None):
    directory = Path(directory)
    freeze = json.loads((directory / "freeze_manifest.json").read_text(encoding="utf-8"))
    if freeze["status"] != "frozen":
        raise ValueError("Snapshot is not marked frozen.")
    for filename, expected in freeze["file_sha256"].items():
        path = directory / filename
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Frozen file is missing or changed: {filename}")

    selected = read_csv(directory / "mtsamples_curated_50.csv")
    ids = [int(row["source_row_id"]) for row in selected]
    if len(ids) != freeze["report_count"] or len(set(ids)) != len(ids):
        raise ValueError("Wrong report count or repeated source IDs.")
    if ids != freeze["selected_source_row_ids"]:
        raise ValueError("Frozen source IDs or their order changed.")
    selection = json.loads((directory / "selection_manifest.json").read_text(encoding="utf-8"))
    if selection["selected_source_row_ids"] != ids:
        raise ValueError("Selection and freeze manifests disagree.")

    annotations = [json.loads(line) for line in
                   (directory / "source_review_annotations.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    if [entry["source_row_id"] for entry in annotations] != ids:
        raise ValueError("Review must cover every frozen report exactly once, in order.")
    decisions = Counter()
    for row, entry in zip(selected, annotations):
        ident = row["source_row_id"]
        text = row["transcription"]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != freeze["transcription_sha256"][ident] or digest != entry["transcription_sha256"]:
            raise ValueError(f"Transcription hash mismatch for source row {ident}.")
        if len(text.split()) != int(row["word_count"]):
            raise ValueError(f"Word count mismatch for source row {ident}.")
        if entry["decision"] not in {"accept", "accept_with_caveat"}:
            raise ValueError(f"Unresolved suitability decision for source row {ident}.")
        if not entry["evidence_quote"] or entry["evidence_quote"] not in text:
            raise ValueError(f"Review evidence is absent from source row {ident}.")
        decisions[entry["decision"]] += 1
    if dict(decisions) != freeze["review_decisions"]:
        raise ValueError("Review decision counts disagree with freeze manifest.")

    source_checked = False
    if source is not None:
        source = Path(source)
        if sha256(source) != freeze["source_sha256"]:
            raise ValueError("Original source file differs from the frozen source hash.")
        raw = read_csv(source)
        for row in selected:
            if row["transcription"] != raw[int(row["source_row_id"])]["transcription"]:
                raise ValueError(f"Source text mismatch for row {row['source_row_id']}.")
        source_checked = True
    return {
        "freeze_id": freeze["freeze_id"], "status": "verified",
        "reports": len(ids), "review_decisions": dict(decisions),
        "frozen_files_checked": len(freeze["file_sha256"]),
        "original_source_checked": source_checked,
        "review_status": freeze["review"]["status"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--source", type=Path,
                        help="Also verify the original mtsamples.csv and exact source text.")
    args = parser.parse_args()
    try:
        result = validate(args.directory, args.source)
    except (ValueError, OSError, KeyError, IndexError) as exc:
        parser.exit(1, f"Freeze validation failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
