"""Read frozen examples without changing the reports or requiring the dataset."""

import csv
import hashlib
import json
from pathlib import Path

from faithfulmed_demo.config import ROOT
from faithfulmed_demo.fixtures import SOURCE

BUILTIN = "Synthetic example · chest pain"


def load_examples(directory: Path = ROOT / "data/curated_baseline"):
    examples = {BUILTIN: {"text": SOURCE, "note": "Synthetic chest-pain report used in the ADK demo."}}
    csv_path = directory / "mtsamples_curated_50.csv"
    if not csv_path.exists():
        return examples, "MTSamples examples are not installed here. You can still paste a report or use the synthetic example."
    try:
        manifest = json.loads((directory / "freeze_manifest.json").read_text(encoding="utf-8"))
        annotations = {str(row["source_row_id"]): row for row in
                       (json.loads(line) for line in (directory / "source_review_annotations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if [int(row["source_row_id"]) for row in rows] != manifest["selected_source_row_ids"]:
            raise ValueError("Frozen report IDs differ.")
        for row in rows:
            identity, text = row["source_row_id"], row["transcription"]
            annotation = annotations[identity]
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != annotation["transcription_sha256"]:
                raise ValueError("Report differs from reviewed source.")
            label = f"MTSamples {identity} · {row['sample_name'].strip()}"
            note = f"{row['medical_specialty'].strip()} · {len(text.split())} words · source row {identity}."
            if annotation.get("source_caveat"):
                note += " Source caveat: " + annotation["source_caveat"]
            examples[label] = {"text": text, "note": note}
        return examples, f"{len(rows)} frozen MTSamples reports available. Selecting an example does not run the model."
    except (OSError, ValueError, KeyError, TypeError, csv.Error):
        return {BUILTIN: examples[BUILTIN]}, "MTSamples files could not be verified. Restore the frozen CSV and review files, or paste a report."
