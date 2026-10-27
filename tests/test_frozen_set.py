"""Frozen inputs must survive reruns and detect changed or incomplete review data."""

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.validate_frozen_set import sha256, validate


class FrozenSetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        texts = ["A test result is still pending.", "A procedure is planned for tomorrow."]
        self.write_csv("mtsamples_curated_50.csv", [
            {"source_row_id": i, "transcription": text, "word_count": len(text.split())}
            for i, text in enumerate(texts)
        ])
        self.write_csv("source.csv", [{"transcription": text} for text in texts])
        self.source = self.directory / "source.csv"
        self.hashes = {str(i): hashlib.sha256(text.encode()).hexdigest()
                       for i, text in enumerate(texts)}
        self.annotations = [
            {"source_row_id": i, "decision": "accept", "evidence_quote": text,
             "transcription_sha256": self.hashes[str(i)]}
            for i, text in enumerate(texts)
        ]
        self.write_annotations()
        (self.directory / "selection_manifest.json").write_text(
            json.dumps({"selected_source_row_ids": [0, 1]}), encoding="utf-8")
        self.freeze = {
            "freeze_id": "test-fixture", "status": "frozen", "report_count": 2,
            "selected_source_row_ids": [0, 1], "transcription_sha256": self.hashes,
            "review_decisions": {"accept": 2}, "review": {"status": "completed"},
            "source_sha256": sha256(self.source),
            "file_sha256": {name: sha256(self.directory / name) for name in
                            ["mtsamples_curated_50.csv", "selection_manifest.json",
                             "source_review_annotations.jsonl"]},
        }
        self.write_freeze()

    def write_csv(self, filename, rows):
        with (self.directory / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def write_annotations(self):
        (self.directory / "source_review_annotations.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in self.annotations), encoding="utf-8")

    def write_freeze(self):
        (self.directory / "freeze_manifest.json").write_text(
            json.dumps(self.freeze), encoding="utf-8")

    def repin_annotations(self):
        self.write_annotations()
        self.freeze["file_sha256"]["source_review_annotations.jsonl"] = sha256(
            self.directory / "source_review_annotations.jsonl")
        self.write_freeze()

    def test_verifies_snapshot_and_original_source(self):
        result = validate(self.directory, self.source)
        self.assertEqual(result["reports"], 2)
        self.assertTrue(result["original_source_checked"])
        self.assertEqual(result["review_status"], "completed")

    def test_changed_input_fails_hash_check(self):
        with (self.directory / "mtsamples_curated_50.csv").open("a", encoding="utf-8") as handle:
            handle.write("changed")
        with self.assertRaisesRegex(ValueError, "Frozen file is missing or changed"):
            validate(self.directory)

    def test_repinning_does_not_hide_missing_review_coverage(self):
        self.annotations.pop()
        self.repin_annotations()
        with self.assertRaisesRegex(ValueError, "Review must cover every frozen report"):
            validate(self.directory)

    def test_fabricated_review_quote_fails_even_if_file_is_repinned(self):
        self.annotations[0]["evidence_quote"] = "The pending result was negative."
        self.repin_annotations()
        with self.assertRaisesRegex(ValueError, "Review evidence is absent"):
            validate(self.directory)

    def test_different_original_source_is_rejected(self):
        self.source.write_text("transcription\nA different report.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Original source file differs"):
            validate(self.directory, self.source)

    def test_sampler_cannot_overwrite_frozen_snapshot(self):
        import pandas as pd
        from EDAs.mtsamples_sampling import export_tables

        existing_hash = sha256(self.directory / "mtsamples_curated_50.csv")
        with self.assertRaisesRegex(ValueError, "Frozen evaluation inputs"):
            export_tables(pd.DataFrame(), pd.DataFrame(), self.directory)
        self.assertEqual(existing_hash, sha256(self.directory / "mtsamples_curated_50.csv"))
        self.assertFalse((self.directory / "mtsamples_curated_50.xlsx").exists())


if __name__ == "__main__":
    unittest.main()
