"""Offline behavioral checks for Zurabi's targeted Refiner contribution."""

import copy
import json
import unittest

from faithfulmed_demo.roles.refiner import refine_state, run_refiner


class RefinerTests(unittest.TestCase):
    def setUp(self):
        self.source = "The result is pending. No allergy. Take 2.5 mg daily."
        self.draft = "Keep this.\nThe result is normal.\nKeep this too."
        original = "The result is normal."
        self.start = self.draft.index(original)
        self.finding = {
            "category": "unsupported", "start": self.start,
            "end": self.start + len(original), "original": original,
            "replacement": "The result is pending.",
            "source_quote": "The result is pending.", "reason": "Result is pending in the note.",
        }
        self.verdict = {"faithful": False, "findings": [self.finding]}

    def test_only_flagged_sentence_changes(self):
        result = run_refiner(self.draft, self.verdict, self.source)
        self.assertEqual(result, "Keep this.\nThe result is pending.\nKeep this too.")

    def test_clean_verdict_preserves_every_character(self):
        for draft in ("", "  Café.\r\nNo allergy.  ", self.draft):
            self.assertEqual(run_refiner(draft, {"faithful": True, "findings": []}), draft)

    def test_json_from_session_state(self):
        self.assertEqual(run_refiner(self.draft, json.dumps(self.verdict), self.source),
                         run_refiner(self.draft, self.verdict, self.source))

    def test_state_delta_and_inputs_are_not_mutated(self):
        state = {"draft": self.draft, "verdict": self.verdict, "source_report": self.source}
        before = copy.deepcopy(state)
        self.assertEqual(set(refine_state(state)), {"revised_draft"})
        self.assertEqual(state, before)

    def test_deletion_only_removes_selected_span(self):
        self.finding.update(replacement="", source_quote="")
        self.assertEqual(run_refiner(self.draft, self.verdict), "Keep this.\n\nKeep this too.")

    def test_repeated_text_uses_exact_offsets(self):
        original = self.finding["original"]
        draft = original + " " + original
        self.finding.update(start=len(original) + 1, end=len(draft))
        self.assertEqual(run_refiner(draft, self.verdict, self.source),
                         original + " The result is pending.")

    def test_multiple_edits_preserve_offsets_and_negation_dose(self):
        draft = "Has allergy. Dose unknown."
        findings = []
        for original, replacement in (("Has allergy.", "No allergy."),
                                      ("Dose unknown.", "Take 2.5 mg daily.")):
            start = draft.index(original)
            findings.append(dict(self.finding, start=start, end=start + len(original),
                                 original=original, replacement=replacement, source_quote=replacement))
        verdict = {"faithful": False, "findings": list(reversed(findings))}
        self.assertEqual(run_refiner(draft, verdict, self.source), "No allergy. Take 2.5 mg daily.")

    def test_stale_or_out_of_range_offsets_rejected(self):
        for changes in ({"start": -1}, {"end": 999}, {"start": True},
                        {"end": self.start}, {"original": "Different text"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                run_refiner(self.draft, {"faithful": False, "findings": [dict(self.finding, **changes)]}, self.source)

    def test_unsupported_replacements_rejected(self):
        for changes in ({"replacement": "Result normal."}, {"source_quote": "Result normal."},
                        {"replacement": " ", "source_quote": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                run_refiner(self.draft, {"faithful": False, "findings": [dict(self.finding, **changes)]}, self.source)
        with self.assertRaises(ValueError):
            run_refiner(self.draft, self.verdict)  # Missing source cannot ground replacement.

    def test_overlap_rejected(self):
        self.verdict["findings"].append(copy.deepcopy(self.finding))
        with self.assertRaises(ValueError):
            run_refiner(self.draft, self.verdict, self.source)

    def test_malformed_or_inconsistent_verdict_rejected(self):
        for verdict in ("not JSON", "[]", None, {}, {"faithful": "true", "findings": []},
                        {"faithful": False, "findings": []},
                        {"faithful": True, "findings": [self.finding]},
                        {"faithful": True, "findings": [], "omissions": ["No allergy"]}):
            with self.subTest(verdict=verdict), self.assertRaises(ValueError):
                run_refiner(self.draft, verdict, self.source)

    def test_omissions_and_unknown_findings_are_explicit_errors(self):
        for category in ("omitted", "fully_supported", "unknown", []):
            with self.subTest(category=category), self.assertRaises(ValueError):
                run_refiner(self.draft, {"faithful": False, "findings": [dict(self.finding, category=category)]}, self.source)

    def test_reason_and_schema_required(self):
        for finding in (dict(self.finding, reason=""), dict(self.finding, replacement=None),
                        {"category": "unsupported"}, "flag", dict(self.finding, extra="ignored?")):
            with self.subTest(finding=finding), self.assertRaises(ValueError):
                run_refiner(self.draft, {"faithful": False, "findings": [finding]}, self.source)

    def test_unicode_offsets(self):
        prefix = "Café 🩺: "
        draft = prefix + self.finding["original"]
        self.finding.update(start=len(prefix), end=len(draft))
        self.assertEqual(run_refiner(draft, self.verdict, self.source), prefix + "The result is pending.")


if __name__ == "__main__":
    unittest.main()
