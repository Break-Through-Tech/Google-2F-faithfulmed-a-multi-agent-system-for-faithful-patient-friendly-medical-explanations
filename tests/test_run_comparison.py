"""Offline checks for the paired comparison runner; nothing here calls an API."""

import contextlib
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from baseline.pipeline import GeminiGenerator
from evaluation import run_comparison as rc
from evaluation import score_outputs
from evaluation.scoring import digest
from faithfulmed_demo import fixtures

ROW = 4998
REPORT = "HISTORY: A synthetic report used only by these tests. " + "More detail. " * 199 + "Last detail."
PLAN = {"pilot_version": "test-pilot", "frozen_set_version": "test-frozen", "source_row_ids": [ROW],
        "reports": {ROW: REPORT}}
REQUIRED_FIELDS = {"source_row_id", "case_id", "system", "generation_model", "frozen_set_version",
                   "pilot_version", "prompt_version", "retrieval_query", "top_k", "retrieved_chunks",
                   "output_text", "output_kind", "status", "error", "elapsed_seconds", "token_usage",
                   "timestamp", "attempt", "attempts", "trace_path", "mode", "source_text"}
INDEX = {"collection": "test-index", "embedding_model": "test", "source_sha256": "abc"}
CHUNK = {"id": "chunk-1", "text": "Background text.", "metadata": {"source_url": "https://example.test/a"},
         "distance": 0.1}


class FakeCollection:
    def __init__(self):
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return {"ids": [[CHUNK["id"]]], "documents": [[CHUNK["text"]]],
                "metadatas": [[CHUNK["metadata"]]], "distances": [[CHUNK["distance"]]]}


class FakeClient:
    def __init__(self, *, text="A scripted answer."):
        self.models = self
        self.text = text
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(candidates=[SimpleNamespace(finish_reason="STOP")], text=self.text,
                               usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=4,
                                                              total_token_count=14))


class ServiceError(Exception):
    code = 429


def live_state(**updates):
    state = {"source_report": REPORT, "retrieval_query": REPORT, "model": "live-model", "run_status": "complete",
             "final_answer": "A released answer.", "revised_draft": "A released answer.", "draft": "First draft.",
             "retrieved_context": [CHUNK], "error": ""}
    return {**state, **updates}


def fake_live_backend(client=None):
    usage = rc.UsageClient(client or FakeClient())
    return rc.Backend("live", "live-model", FakeCollection(), GeminiGenerator(usage, model="live-model"),
                      INDEX, usage=usage, check_model=True)


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.output = self.folder / "results.json"
        plan = patch.object(rc, "load_plan", return_value=PLAN)
        plan.start()
        self.addCleanup(plan.stop)

    def run_cli(self, *extra):
        with quiet():
            rc.main(["--offline", "--output", str(self.output), *extra])
        return self.records()

    def records(self):
        records = json.loads(self.output.read_text(encoding="utf-8"))["records"]
        return {record["system"]: record for record in records}

    def run_live(self, backend=None, **kwargs):
        with quiet():
            return rc.run_comparison(PLAN, list(rc.SYSTEMS), backend or fake_live_backend(), self.output, **kwargs)


class OfflineRunTests(RunnerTestCase):
    def test_both_systems_save_complete_records_without_api_calls(self):
        with (patch("faithfulmed_demo.config.model_client", side_effect=AssertionError("API")) as client,
              patch("google.genai.Client", side_effect=AssertionError("API")) as genai_client,
              patch("google.adk.models.google_llm.Gemini.generate_content_async",
                    side_effect=AssertionError("API")) as adk_model,
              patch("retrieval.gemini_chroma.GeminiEmbedder", side_effect=AssertionError("API")) as embedder,
              patch("retrieval.gemini_chroma.open_collection", side_effect=AssertionError("API")) as index):
            records = self.run_cli()
        for mock in (client, genai_client, adk_model, embedder, index):
            mock.assert_not_called()
        self.assertEqual(set(records), {"baseline", "adk"})
        for record in records.values():
            self.assertLessEqual(REQUIRED_FIELDS, set(record))
            self.assertEqual(record["source_row_id"], ROW)
            self.assertEqual(record["mode"], "offline-scripted")
            self.assertEqual(record["generation_model"], rc.OFFLINE_MODEL)
            self.assertEqual(record["output_kind"], "final_answer")
            self.assertEqual(record["output_text"], rc.SCRIPTED_ANSWER)
            self.assertEqual(record["top_k"], 3)
            self.assertEqual(record["retrieved_chunks"][0]["id"], rc.SCRIPTED_CHUNK["id"])
            self.assertEqual(record["attempt"], 1)
        self.assertEqual(records["baseline"]["status"], "ok")
        self.assertEqual(records["adk"]["status"], "complete")
        comparison = json.loads(self.output.read_text(encoding="utf-8"))["retrieval_comparison"]
        self.assertEqual([entry["result"] for entry in comparison], ["match"])

    def test_saved_source_is_the_pilot_report_not_the_chest_pain_fixture(self):
        with patch.object(rc, "run_baseline", wraps=rc.run_baseline) as baseline:
            records = self.run_cli()
        self.assertNotEqual(REPORT, fixtures.SOURCE)
        for record in records.values():
            self.assertEqual(record["source_text"], REPORT)
            self.assertEqual(record["source_digest"], digest(REPORT))
            self.assertEqual(record["retrieval_query"], REPORT.strip())
        self.assertEqual(baseline.call_args.args[0].clinical_text, REPORT)
        trace = json.loads((self.output.parent / records["adk"]["trace_path"]).read_text(encoding="utf-8"))
        self.assertEqual(trace["state"]["source_report"], REPORT)
        self.assertEqual(trace["state"]["retrieval_query"], REPORT)
        quote = trace["state"]["atoms"][0]["source_quote"]
        self.assertIn(quote, REPORT)
        self.assertNotIn(quote, fixtures.SOURCE)

    def test_adk_trace_holds_state_and_events_and_says_it_was_scripted(self):
        records = self.run_cli()
        self.assertIsNone(records["baseline"]["trace_path"])
        trace = json.loads((self.output.parent / records["adk"]["trace_path"]).read_text(encoding="utf-8"))
        self.assertEqual(trace["runner_mode"], "offline-scripted")
        self.assertIn("scripted", trace["note"])
        self.assertEqual(trace["state"]["run_status"], "complete")
        self.assertEqual(
            list(dict.fromkeys(event["author"] for event in trace["events"] if event.get("content"))),
            ["Intake", "Extractor", "ClinicalExtractor", "QuoteCheck", "Simplifier", "Verifier", "Refiner", "Readability"])

    def test_scripted_calls_do_not_outlast_the_offline_attempt(self):
        from faithfulmed_demo import agent
        from retrieval import gemini_chroma

        originals = (agent.run_simplifier, agent.verify, gemini_chroma.search)
        self.run_cli()
        self.assertEqual((agent.run_simplifier, agent.verify, gemini_chroma.search), originals)

    def test_a_scripted_atom_with_a_bad_quote_is_still_rejected(self):
        with patch.object(rc, "scripted_atoms", return_value=json.dumps(
                [{"text": "Fact.", "type": "diagnosis", "assertion": "uncertain", "source_quote": "Not in the report."}])):
            record = self.run_cli("--systems", "adk")["adk"]
        self.assertEqual((record["status"], record["output_kind"]), ("failed", None))

    def test_needs_review_stays_a_draft(self):
        verdict = {"issues": [{"category": "omission", "claim": "", "replacement": "Missing fact.",
                               "reason": "Test", "source_quote": ""}], "supported_examples": [], "scope": "test"}
        with patch("faithfulmed_demo.agent.judge", new=AsyncMock(return_value=verdict)):
            records = self.run_cli("--systems", "adk")
        record = records["adk"]
        self.assertEqual(record["status"], "needs_review")
        self.assertEqual(record["output_kind"], "needs_review_draft")
        self.assertEqual(record["output_text"], rc.SCRIPTED_ANSWER)

    def test_resume_skips_completed_records(self):
        first = self.run_cli()
        with (patch.object(rc, "run_baseline", side_effect=AssertionError("repeated")) as baseline,
              patch.object(rc, "invoke_adk", side_effect=AssertionError("repeated")) as adk):
            second = self.run_cli()
        baseline.assert_not_called()
        adk.assert_not_called()
        self.assertEqual(first, second)

    def test_failures_are_kept_and_only_retried_with_the_flag(self):
        with (patch.object(rc, "run_baseline", side_effect=RuntimeError("forced failure")),
              patch("faithfulmed_demo.agent.validate_source_quotes", side_effect=ValueError("bad quote"))):
            failed = self.run_cli()
        self.assertEqual(failed["baseline"]["status"], "error")
        self.assertEqual(failed["baseline"]["error"]["message"], "forced failure")
        self.assertEqual(failed["adk"]["status"], "failed")
        self.assertIsNone(failed["adk"]["output_kind"])
        self.assertEqual(failed["adk"]["output_text"], "")
        first_trace = failed["adk"]["trace_path"]

        with patch.object(rc, "run_baseline", side_effect=AssertionError("retried")) as baseline:
            unchanged = self.run_cli()
        baseline.assert_not_called()
        self.assertEqual(unchanged, failed)

        retried = self.run_cli("--retry-errors")
        for system, status in (("baseline", "ok"), ("adk", "complete")):
            self.assertEqual(retried[system]["status"], status)
            self.assertEqual(retried[system]["attempt"], 2)
            self.assertEqual(len(retried[system]["attempts"]), 1)
            self.assertEqual(retried[system]["attempts"][0]["attempt"], 1)
            self.assertEqual(retried[system]["attempts"][0]["status"], failed[system]["status"])
        self.assertEqual(retried["baseline"]["attempts"][0]["error"]["message"], "forced failure")
        self.assertNotEqual(retried["adk"]["trace_path"], first_trace)
        self.assertTrue((self.output.parent / first_trace).exists())

    def test_retry_keeps_the_full_failure_history(self):
        with patch.object(rc, "run_baseline", side_effect=RuntimeError("first")):
            self.run_cli("--systems", "baseline")
        with patch.object(rc, "run_baseline", side_effect=RuntimeError("second")):
            self.run_cli("--systems", "baseline", "--retry-errors")
        record = self.run_cli("--systems", "baseline", "--retry-errors")["baseline"]
        self.assertEqual(record["attempt"], 3)
        self.assertEqual([entry["error"]["message"] for entry in record["attempts"]], ["first", "second"])
        self.assertNotIn("attempts", record["attempts"][0])

    def test_changed_settings_add_a_record_and_keep_the_old_one(self):
        self.run_cli("--systems", "baseline")
        before = json.loads(self.output.read_text(encoding="utf-8"))["records"][0]
        with patch.object(rc, "prompt_version", return_value="changed-prompt"):
            with quiet():
                rc.main(["--offline", "--output", str(self.output), "--systems", "baseline"])
        records = json.loads(self.output.read_text(encoding="utf-8"))["records"]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], before)
        self.assertEqual(records[1]["prompt_version"], "changed-prompt")

    def test_limit_counts_new_calls(self):
        self.assertEqual(set(self.run_cli("--limit", "1")), {"baseline"})
        self.assertEqual(set(self.run_cli("--limit", "1")), {"baseline", "adk"})


class LiveLogicTests(RunnerTestCase):
    def test_both_systems_get_the_full_report_and_top_k_three(self):
        client = FakeClient()
        backend = fake_live_backend(client)
        with patch.object(rc, "invoke_adk", new=AsyncMock(return_value=live_state())) as adk:
            self.run_live(backend)
        self.assertEqual(adk.await_args.args[0], REPORT)
        self.assertEqual(backend.collection.calls[0]["query_texts"], [REPORT.strip()])
        self.assertEqual(backend.collection.calls[0]["n_results"], 3)
        self.assertIn("synthetic report", client.calls[0]["contents"])
        self.assertEqual(self.records()["baseline"]["token_usage"]["total_tokens"], 14)

    def test_different_passages_are_reported_as_a_mismatch(self):
        other = {**CHUNK, "id": "chunk-2"}
        with patch.object(rc, "invoke_adk", new=AsyncMock(return_value=live_state(retrieved_context=[other]))):
            state = self.run_live()
        self.assertEqual(state["retrieval_comparison"][0]["result"], "mismatch")

    def test_quota_error_stops_the_batch_and_saves_the_failure(self):
        with (patch.object(rc, "run_baseline", side_effect=ServiceError()),
              patch.object(rc, "invoke_adk", new=AsyncMock()) as adk):
            self.run_live()
        adk.assert_not_awaited()
        self.assertEqual(self.records()["baseline"]["error"]["service_code"], 429)

    def test_exception_from_adk_is_saved_without_its_raw_message(self):
        with patch.object(rc, "invoke_adk", new=AsyncMock(side_effect=OSError("secret-request-detail"))):
            self.run_live()
        record = self.records()["adk"]
        self.assertEqual(record["status"], "error")
        self.assertNotIn("secret-request-detail", json.dumps(record))

    def test_report_starting_with_a_slash_is_not_sent_to_adk(self):
        plan = {**PLAN, "reports": {ROW: "/offline"}}
        with patch.object(rc, "invoke_adk", new=AsyncMock()) as adk, quiet():
            rc.run_comparison(plan, ["adk"], fake_live_backend(), self.output)
        adk.assert_not_awaited()
        self.assertEqual(self.records()["adk"]["status"], "error")


class AdkOutcomeTests(unittest.TestCase):
    def fields(self, **updates):
        return rc.adk_fields(live_state(**updates), expected_note=REPORT, expected_query=REPORT, model="live-model")

    def test_complete_is_the_only_final_answer(self):
        fields = self.fields()
        self.assertEqual((fields["status"], fields["output_kind"]), ("complete", "final_answer"))
        self.assertEqual(fields["output_text"], "A released answer.")

    def test_empty_complete_answer_is_not_a_success(self):
        for answer in ("", "   ", None):
            fields = self.fields(final_answer=answer)
            self.assertEqual((fields["status"], fields["output_kind"]), ("error", None))

    def test_drafts_keep_their_status_and_prefer_the_revised_text(self):
        for status in ("needs_review", "needs_simplification"):
            fields = self.fields(run_status=status, final_answer="", revised_draft="Revised.")
            self.assertEqual((fields["status"], fields["output_kind"]), (status, "needs_review_draft"))
            self.assertEqual(fields["output_text"], "Revised.")
        fields = self.fields(run_status="needs_review", final_answer="", revised_draft="")
        self.assertEqual(fields["output_text"], "First draft.")

    def test_draft_with_no_text_is_an_error(self):
        fields = self.fields(run_status="needs_review", final_answer="", revised_draft="", draft="")
        self.assertEqual((fields["status"], fields["output_kind"]), ("error", None))

    def test_failed_and_unknown_statuses_release_nothing(self):
        failed = self.fields(run_status="failed", final_answer="", error="Stage stopped.")
        self.assertEqual((failed["status"], failed["output_kind"], failed["output_text"]), ("failed", None, ""))
        self.assertEqual(failed["error"]["message"], "Stage stopped.")
        for status in ("running", "invalid", None):
            self.assertEqual(self.fields(run_status=status)["status"], "error")

    def test_wrong_input_or_model_is_an_error_even_when_complete(self):
        self.assertEqual(self.fields(retrieval_query=REPORT[:1500])["status"], "error")
        self.assertEqual(self.fields(source_report="Other note.")["status"], "error")
        self.assertEqual(self.fields(model="other-model")["status"], "error")

    def test_quota_code_is_read_from_a_failed_adk_message(self):
        self.assertEqual(rc.stop_code({"error": {"message": "Simplifier stopped: X (service code 429)."}}), 429)
        self.assertIsNone(rc.stop_code({"error": {"message": "Simplifier stopped: X (service code 500)."}}))


class PreflightTests(unittest.TestCase):
    def test_missing_index_stops_without_creating_an_empty_one(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "missing"
            with self.assertRaisesRegex(ValueError, "No Gemini index"):
                rc.open_live_index(target)
            self.assertFalse(target.exists())

    def test_adk_loaded_with_another_model_stops_the_run(self):
        code = ("import os\n"
                "os.environ['FAITHFULMED_MODEL'] = 'first-model'\n"
                "from evaluation import run_comparison as rc\n"
                "rc.check_adk_settings('first-model')\n"
                "try:\n"
                "    rc.check_adk_settings('second-model')\n"
                "except ValueError:\n"
                "    print('refused')\n")
        self.assertIn("refused", self.python(code))

    def test_model_argument_reaches_a_freshly_loaded_adk_pipeline(self):
        code = ("from evaluation import run_comparison as rc\n"
                "rc.check_adk_settings('chosen-model')\n"
                "from faithfulmed_demo.agent import build_agent\n"
                "print(build_agent().sub_agents[1].sub_agents[0].model)\n")
        self.assertIn("chosen-model", self.python(code))

    @staticmethod
    def python(code):
        env = {key: value for key, value in os.environ.items() if key != "FAITHFULMED_MODEL"}
        return subprocess.run([sys.executable, "-c", code], cwd=rc.ROOT, env=env, check=True,
                              capture_output=True, text=True, timeout=120).stdout


class ScoringExportTests(RunnerTestCase):
    def setUp(self):
        super().setUp()
        with (self.folder / "mtsamples_curated_50.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["source_row_id", "transcription"])
            writer.writeheader()
            writer.writerow({"source_row_id": ROW, "transcription": REPORT})
        self.facts = self.folder / "facts"
        self.facts.mkdir()
        (self.facts / f"source_row_{ROW}.json").write_text(json.dumps({
            "source_report": REPORT,
            "key_facts": [{"id": "K1", "text": "A synthetic report.", "source_quote": "A synthetic report"}],
            "source_digest": digest(REPORT)}), encoding="utf-8")
        self.scoring = self.folder / "scoring.json"

    def export(self):
        with quiet():
            rc.export_scoring_input(self.output, self.facts, self.scoring, directory=self.folder)
        return {job["system"]: job for job in json.loads(self.scoring.read_text(encoding="utf-8"))["records"]}

    def test_labels_are_converted_and_the_evaluator_accepts_the_file(self):
        state = live_state(run_status="needs_review", final_answer="", revised_draft="A draft.")
        with patch.object(rc, "invoke_adk", new=AsyncMock(return_value=state)):
            self.run_live()
        jobs = self.export()
        self.assertEqual((jobs["baseline"]["output_kind"], jobs["baseline"]["run_status"]), ("final", "ok"))
        self.assertEqual((jobs["adk"]["output_kind"], jobs["adk"]["run_status"]), ("draft", "needs_review"))
        self.assertEqual(jobs["adk"]["output"], "A draft.")
        self.assertEqual(jobs["baseline"]["retrieved_context"], [{"id": CHUNK["id"], "text": CHUNK["text"]}])
        results = self.folder / "scored.json"
        with patch.object(score_outputs, "assess_output", side_effect=ValueError("no judge in tests")), quiet():
            scored = score_outputs.run(list(jobs.values()), results, model="test-judge")
        self.assertEqual(len(scored["records"]), 2)
        self.assertEqual({record["output_kind"] for record in scored["records"]}, {"final", "draft"})

    def test_failed_generation_stays_in_the_denominator(self):
        with (patch.object(rc, "run_baseline", side_effect=RuntimeError("forced")),
              patch.object(rc, "invoke_adk", new=AsyncMock(return_value=live_state()))):
            self.run_live()
        job = self.export()["baseline"]
        self.assertEqual((job["output_kind"], job["run_status"], job["output"]), ("final", "error", ""))
        result = score_outputs.run_job(job, model="test-judge")
        self.assertEqual(result["status"], "generation_failed")

    def test_offline_records_cannot_be_scored(self):
        self.run_cli()
        with self.assertRaisesRegex(ValueError, "Offline"):
            self.export()

    def test_two_groups_of_settings_are_refused(self):
        with patch.object(rc, "invoke_adk", new=AsyncMock(return_value=live_state())):
            self.run_live()
            with patch.object(rc, "prompt_version", return_value="changed"):
                self.run_live()
        with self.assertRaisesRegex(ValueError, "more than one group"):
            self.export()

    def test_key_facts_from_different_text_are_refused(self):
        with patch.object(rc, "invoke_adk", new=AsyncMock(return_value=live_state())):
            self.run_live()
        path = self.facts / f"source_row_{ROW}.json"
        path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), "source_report": "Other."}),
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "different text"):
            self.export()


FROZEN_CSV = rc.DEFAULT_DIRECTORY / "mtsamples_curated_50.csv"


@unittest.skipUnless(FROZEN_CSV.exists(), "The frozen CSV is local and not stored in Git.")
class FrozenPilotTests(unittest.TestCase):
    def test_offline_run_saves_each_real_pilot_report(self):
        plan = rc.load_plan(rc.DEFAULT_IDS)
        with tempfile.TemporaryDirectory() as folder, quiet():
            state = rc.run_comparison(plan, list(rc.SYSTEMS), rc.offline_backend(), Path(folder) / "results.json")
        self.assertEqual(len(state["records"]), 10)
        for record in state["records"]:
            self.assertEqual(record["source_text"], plan["reports"][record["source_row_id"]])
            self.assertEqual(record["mode"], "offline-scripted")
            self.assertNotEqual(record["source_text"], fixtures.SOURCE)

    def test_pilot_reports_load_and_are_safe_to_send_to_adk(self):
        plan = rc.load_plan(rc.DEFAULT_IDS)
        self.assertEqual(len(plan["source_row_ids"]), 5)
        for text in plan["reports"].values():
            self.assertTrue(text.strip())
            self.assertEqual(text, text.strip())
            self.assertFalse(text.startswith("/"))


if __name__ == "__main__":
    unittest.main()
