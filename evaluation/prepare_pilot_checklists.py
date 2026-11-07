"""Materialize the reviewed source-only pilot inventories, without model calls."""

import argparse
import hashlib
import json
from pathlib import Path

from .scoring import digest, validate_key_facts
from .validate_frozen_set import DEFAULT_DIRECTORY, read_csv, validate

DEFINITIONS = Path(__file__).with_name("pilot_key_facts_v1.json")


def prepare(output_dir):
    validate(DEFAULT_DIRECTORY)
    definitions = json.loads(DEFINITIONS.read_text(encoding="utf-8"))
    pilot = json.loads(Path("evaluation/pilot_ids.json").read_text(encoding="utf-8"))
    rows = {int(r["source_row_id"]): r for r in read_csv(DEFAULT_DIRECTORY / "mtsamples_curated_50.csv")}
    if set(map(int, definitions["reports"])) != set(pilot["source_row_ids"]):
        raise ValueError("Checklist reports do not match the pilot selection.")
    artifacts = []
    for row_id in pilot["source_row_ids"]:
        row = rows[row_id]
        facts = [dict(id=f"R{row_id}-K{index:02d}", text=text, source_quote=quote)
                 for index, (text, quote) in enumerate(definitions["reports"][str(row_id)], 1)]
        validate_key_facts(row["transcription"], facts)
        artifacts.append(dict(inventory_version=definitions["inventory_version"],
            source_row_id=row_id, sample_name=row["sample_name"],
            frozen_set_version=pilot["frozen_set_version"],
            source_report=row["transcription"], source_digest=digest(row["transcription"]),
            source_text_sha256=hashlib.sha256(row["transcription"].encode("utf-8")).hexdigest(),
            key_facts=facts, key_facts_digest=digest(facts),
            preparation="Source-only desk review; no generation outputs read during preparation; no API calls.",
            timing="Prepared after an earlier generation run" if row_id == 4998 else "Prepared before pilot generation in this work"))
    output_dir = Path(output_dir)
    paths = [output_dir / f"source_row_{r['source_row_id']}.json" for r in artifacts]
    if any(p.exists() for p in paths) or (output_dir / "manifest.json").exists():
        raise ValueError("Choose a fresh version directory; inventories are not overwritten.")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, artifact in zip(paths, artifacts):
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    manifest = dict(inventory_version=definitions["inventory_version"],
        definition_digest=digest(definitions), reports=[dict(source_row_id=r["source_row_id"],
        key_fact_count=len(r["key_facts"]), source_digest=r["source_digest"],
        key_facts_digest=r["key_facts_digest"]) for r in artifacts],
        file_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for report in prepare(args.output_dir):
        print(f"{report['source_row_id']}: {len(report['key_facts'])} verified source anchors")


if __name__ == "__main__":
    main()
