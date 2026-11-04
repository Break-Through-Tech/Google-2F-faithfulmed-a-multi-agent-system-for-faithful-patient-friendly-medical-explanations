"""Run the baseline and ADK pipeline on the same frozen reports and save every result.

This only connects existing code. See evaluation/RUNNING_COMPARISONS.md.
"""

import argparse
import asyncio
import hashlib
import inspect
import json
import os
import re
import time
from collections import Counter
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from baseline.pipeline import PROMPT_VERSION, BaselineInput, GeminiGenerator, run_baseline

from .score_outputs import write_json
from .scoring import digest, safe_error, validate_key_facts
from .validate_frozen_set import DEFAULT_DIRECTORY, read_csv, validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IDS = ROOT / "evaluation/pilot_ids.json"
RESULTS_DIRECTORY = ROOT / "data/comparison_results"
SCHEMA_VERSION = 1
DEFAULT_MODEL = "gemini-3.8-flash"
OFFLINE_MODEL = "offline-stub-not-gemini"
OFFLINE_MODE = "offline-scripted"
SCRIPTED_ANSWER = "This is a scripted test draft. No model wrote it. Do not use it as medical advice."
SCRIPTED_CHUNK = {"id": "offline-scripted-chunk-1", "text": "Scripted background text. This is not from MedlinePlus.",
                  "metadata": {"source_url": "https://example.invalid/offline-scripted"}, "distance": None}
TOP_K = 3
QUERY_RULE = "full-report-text"
SYSTEMS = ("baseline", "adk")
RETRYABLE = {"error", "failed", "no_context"}
DRAFT_STATUSES = {"needs_review", "needs_simplification"}
# The same access and quota errors that stop evaluation/score_outputs.py.
STOP_CODES = {400, 401, 403, 404, 429}
ADK_SOURCES = ("faithfulmed_demo/agent.py", "faithfulmed_demo/config.py", "faithfulmed_demo/fixtures.py",
               "faithfulmed_demo/refiner_adapter.py", "faithfulmed_demo/roles/*.py", "evaluation/readability.py")


@dataclass
class Backend:
    """Everything that differs between an offline run and a live run."""

    mode: str
    model: str
    collection: Any
    generator: Any
    index: dict
    usage: Any = None
    check_model: bool = False


class UsageClient:
    """Remember the token counts of a Gemini response that GeminiGenerator discards."""

    def __init__(self, client):
        self.client = client
        self.models = self
        self.counts = None

    def generate_content(self, **kwargs):
        response = self.client.models.generate_content(**kwargs)
        self.counts = token_counts(getattr(response, "usage_metadata", None))
        return response


def token_counts(usage):
    if usage is None:
        return None
    return {"prompt_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None)}


def code_version(*patterns):
    """Fingerprint source files, so a changed prompt or temperature gets a new record key."""
    hasher = hashlib.sha256()
    paths = sorted({path for pattern in patterns for path in ROOT.glob(pattern)})
    if not paths:
        raise ValueError("No source files found to fingerprint.")
    for path in paths:
        hasher.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        hasher.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return hasher.hexdigest()[:12]


def prompt_version(system):
    if system == "baseline":
        return f"{PROMPT_VERSION}+{code_version('baseline/pipeline.py')}"
    return f"adk-stages+{code_version(*ADK_SOURCES)}"


def load_plan(ids_path, directory=DEFAULT_DIRECTORY):
    """Confirm the frozen set is unchanged, then read the requested reports."""
    plan = json.loads(Path(ids_path).read_text(encoding="utf-8"))
    freeze = validate(directory)
    if plan["frozen_set_version"] != freeze["freeze_id"]:
        raise ValueError("The ID list names a different frozen set than the one on disk.")
    rows = {int(row["source_row_id"]): row["transcription"]
            for row in read_csv(Path(directory) / "mtsamples_curated_50.csv")}
    ids = plan["source_row_ids"]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("The ID list must be nonempty with no repeated IDs.")
    missing = [row_id for row_id in ids if row_id not in rows]
    if missing:
        raise ValueError(f"These IDs are not in the frozen set: {missing}")
    return {"pilot_version": plan["pilot_version"], "frozen_set_version": plan["frozen_set_version"],
            "source_row_ids": ids, "reports": {row_id: rows[row_id] for row_id in ids}}


class OfflineCollection:
    """Scripted search results for the baseline, shaped like a Chroma response."""

    def query(self, **kwargs):
        return {"ids": [[SCRIPTED_CHUNK["id"]]], "documents": [[SCRIPTED_CHUNK["text"]]],
                "metadatas": [[SCRIPTED_CHUNK["metadata"]]], "distances": [[SCRIPTED_CHUNK["distance"]]]}


class OfflineGenerator:
    model = OFFLINE_MODEL

    def generate(self, **kwargs):
        return SCRIPTED_ANSWER


def offline_backend():
    return Backend(OFFLINE_MODE, OFFLINE_MODEL, OfflineCollection(), OfflineGenerator(),
                   {"collection": OFFLINE_MODE})


def scripted_atoms(report):
    """One atom quoting the real report, so the real quote check still has something to verify."""
    return json.dumps([{"text": "Scripted fact for an offline test.", "type": "diagnosis", "assertion": "uncertain",
                        "source_quote": report.strip()[:80].strip()}])


def use_scripted_extractor(agent, report):
    """Replace only the Extractor's Gemini model; ADK still parses and saves its output."""
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    class ScriptedLlm(BaseLlm):
        response_text: str

        async def generate_content_async(self, llm_request, stream=False):
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=self.response_text)]))

    agent.find_agent("ClinicalExtractor").model = ScriptedLlm(model=OFFLINE_MODEL,
                                                              response_text=scripted_atoms(report))


@contextmanager
def scripted_adk_calls():
    """Replace retrieval, Simplifier and Verifier calls for the length of one offline attempt."""
    verdict = {"issues": [], "supported_examples": [], "scope": "Scripted offline check; not a real verification."}
    with (patch("retrieval.gemini_chroma.search", return_value=[dict(SCRIPTED_CHUNK)]),
          patch("faithfulmed_demo.agent.run_simplifier", return_value=SCRIPTED_ANSWER),
          patch("faithfulmed_demo.agent.verify", return_value=verdict)):
        yield


def open_live_index(db_path=None):
    """Check the index exists first, because opening a missing one leaves an empty database behind."""
    from retrieval.gemini_chroma import COLLECTION, DB_PATH, MODEL, open_collection

    db_path = Path(db_path or DB_PATH)
    if not (db_path / "chroma.sqlite3").is_file():
        raise ValueError(f"No Gemini index at {db_path}. See data_pipeline/GEMINI_MEDLINEPLUS.md.")
    target = open_collection(db_path)
    if not target.count():
        raise ValueError(f"The Gemini index at {db_path} is empty.")
    return target, {"collection": COLLECTION, "embedding_model": MODEL,
                    "source_sha256": target.metadata.get("source_sha256")}


def check_adk_settings(model):
    """ADK reads its model once at import, so a mismatch has to stop the run."""
    from retrieval.gemini_chroma import search

    if inspect.signature(search).parameters["top_k"].default != TOP_K:
        raise ValueError(f"ADK's retrieval no longer uses top_k {TOP_K}.")
    os.environ["FAITHFULMED_MODEL"] = model
    from faithfulmed_demo import agent

    if agent.MODEL != model:
        raise ValueError(f"ADK is already loaded with {agent.MODEL}, not {model}. Use a new process.")


def live_backend(client, model, index_target, index):
    from retrieval.gemini_chroma import GeminiEmbedder, GeminiTextQueryCollection

    usage = UsageClient(client)
    return Backend("live", model, GeminiTextQueryCollection(index_target, GeminiEmbedder(client)),
                   GeminiGenerator(usage, model=model), index, usage=usage, check_model=True)


def describe_error(exc):
    """Keep our own error messages, but never a raw service error, which can hold request details."""
    result = safe_error(exc)
    if type(exc) in (ValueError, RuntimeError):
        result["message"] = str(exc)
    return result


def normalize_chunks(chunks):
    return [{"id": chunk.get("id"), "url": (chunk.get("metadata") or {}).get("source_url"),
             "text": chunk.get("text"), "distance": chunk.get("distance")} for chunk in chunks or []]


def run_baseline_attempt(backend, text):
    fields = {"retrieval_query": text, "retrieved_chunks": [], "output_text": "", "output_kind": None,
              "error": None, "token_usage": None}
    if backend.usage:
        backend.usage.counts = None
    try:
        result = run_baseline(BaselineInput("comparison", text, text), collection=backend.collection,
                              generator=backend.generator, top_k=TOP_K)
        fields.update(retrieval_query=result["retrieval_query"], status=result["status"],
                      retrieved_chunks=normalize_chunks(result["retrieved_context"]),
                      output_text=result["model_output"],
                      output_kind="final_answer" if result["status"] == "ok" else None)
    except Exception as exc:
        fields.update(status="error", error=describe_error(exc))
    if backend.usage and backend.usage.counts:
        fields["token_usage"] = {"scope": "the one generation call", **backend.usage.counts}
    return fields


def adk_fields(state, *, expected_note, expected_query, model=None):
    """Turn final ADK state into record fields. A draft is never presented as a final answer."""
    status = state.get("run_status")
    fields = {"retrieval_query": state.get("retrieval_query", ""), "output_text": "", "output_kind": None,
              "retrieved_chunks": normalize_chunks(state.get("retrieved_context")),
              "status": "error", "error": None}

    def problem(message):
        return {**fields, "error": {"message": message}}

    if "source_report" in state and (state["source_report"] != expected_note
                                     or state.get("retrieval_query") != expected_query):
        return problem("ADK did not receive the expected note and query.")
    if model and state.get("model") != model:
        return problem(f"ADK ran with {state.get('model')} instead of {model}.")
    if status == "failed":
        return {**fields, "status": "failed",
                "error": {"message": state.get("error") or "ADK stopped without an error message."}}
    if status == "complete":
        answer = state.get("final_answer") or ""
        if not answer.strip():
            return problem("ADK reported complete with an empty final answer.")
        return {**fields, "status": "complete", "output_text": answer, "output_kind": "final_answer"}
    if status in DRAFT_STATUSES:
        draft = state.get("revised_draft") or state.get("draft") or ""
        if not draft.strip():
            return problem(f"ADK ended with {status} and no draft text.")
        return {**fields, "status": status, "output_text": draft, "output_kind": "needs_review_draft"}
    return problem(f"ADK ended with unexpected run_status {status!r}.")


async def invoke_adk(message, session_id, events, scripted=False):
    """The Runner pattern from smoke.py, without its SystemExit and with one session per record."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from faithfulmed_demo.agent import build_agent

    app, user = "faithfulmed_demo", "comparison"
    sessions = InMemorySessionService()
    await sessions.create_session(app_name=app, user_id=user, session_id=session_id)
    agent = build_agent()
    if scripted:
        use_scripted_extractor(agent, message)
    runner = Runner(agent=agent, app_name=app, session_service=sessions)
    async for event in runner.run_async(user_id=user, session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=message)])):
        events.append(event)
    session = await sessions.get_session(app_name=app, user_id=user, session_id=session_id)
    return session.state


def adk_token_usage(events):
    """ADK events only report calls made by the Extractor's LlmAgent."""
    used = [token_counts(event.usage_metadata) for event in events if event.usage_metadata]
    if not used:
        return None
    return {"scope": "Extractor only; Simplifier and Verifier calls are not reported in ADK events",
            **{key: sum(entry[key] or 0 for entry in used)
               for key in ("prompt_tokens", "output_tokens", "total_tokens")}}


def run_adk_attempt(backend, text, session_id):
    events, state = [], None
    scripted = backend.mode == OFFLINE_MODE
    failure = {"retrieval_query": text, "retrieved_chunks": [], "output_text": "", "output_kind": None,
               "status": "error"}
    if text.startswith("/"):
        # ADK would treat this as a command instead of a note.
        return {**failure, "token_usage": None,
                "error": {"message": "The report starts with '/', which ADK reads as a command."}}, None
    try:
        with scripted_adk_calls() if scripted else nullcontext():
            state = asyncio.run(invoke_adk(text, session_id, events, scripted=scripted))
        fields = adk_fields(state, expected_note=text, expected_query=text,
                            model=backend.model if backend.check_model else None)
    except Exception as exc:
        fields = {**failure, "error": describe_error(exc)}
    fields["token_usage"] = adk_token_usage(events)
    trace = {"runner_mode": backend.mode, "state": state,
             "events": [event.model_dump(mode="json", exclude_none=True) for event in events]}
    if scripted:
        trace["note"] = ("ADK's own state and messages say live because it ran its live path, "
                         "but its model, retrieval, Simplifier and Verifier calls were scripted.")
    return fields, trace


def save_trace(output, record, trace):
    """Each attempt gets its own file, so a retry never overwrites an earlier trace."""
    model = re.sub(r"[^A-Za-z0-9.-]+", "-", record["generation_model"])
    name = (f"row{record['source_row_id']}-{record['system']}-{model}-"
            f"{record['settings_digest'][:10]}-attempt{record['attempt']}.json")
    path = output.parent / "traces" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(name + ".tmp")
    temporary.write_text(json.dumps(trace, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path.relative_to(output.parent).as_posix()


def build_settings(backend, plan, system):
    shared = {"mode": backend.mode, "frozen_set_version": plan["frozen_set_version"],
              "pilot_version": plan["pilot_version"], "query_rule": QUERY_RULE, "top_k": TOP_K,
              "retrieval_index": backend.index}
    return {**shared, "prompt_version": prompt_version(system)}, digest(shared)


def attempt_once(backend, plan, system, row_id, output, previous):
    settings, retrieval_digest = build_settings(backend, plan, system)
    settings_digest = digest(settings)
    attempt = previous["attempt"] + 1 if previous else 1
    text = plan["reports"][row_id]
    record = {"record_key": record_key(row_id, system, backend.model, settings_digest),
              "source_row_id": row_id, "case_id": f"source-row-{row_id}", "system": system,
              "generation_model": backend.model, "frozen_set_version": plan["frozen_set_version"],
              "pilot_version": plan["pilot_version"], "prompt_version": settings["prompt_version"],
              "mode": backend.mode, "settings": settings, "settings_digest": settings_digest,
              "retrieval_settings_digest": retrieval_digest, "top_k": TOP_K, "attempt": attempt}
    started = time.perf_counter()
    trace = None
    if system == "baseline":
        fields = run_baseline_attempt(backend, text)
    else:
        fields, trace = run_adk_attempt(backend, text, f"{row_id}-attempt-{attempt}")
    record.update(fields)
    record.update(source_text=text, source_digest=digest(text), elapsed_seconds=round(time.perf_counter() - started, 3),
                  timestamp=datetime.now(timezone.utc).isoformat(), trace_path=None)
    if trace is not None:
        record["trace_path"] = save_trace(output, record, trace)
    past = previous.get("attempts", []) if previous else []
    earlier = {key: value for key, value in previous.items() if key != "attempts"} if previous else None
    record["attempts"] = past + [earlier] if earlier else []
    return record


def record_key(row_id, system, model, settings_digest):
    return f"{row_id}|{system}|{model}|{settings_digest}"


def compare_retrieval(records):
    """Confirm both systems used the same query, top_k and passages for each report."""
    pairs = {}
    for record in records:
        group = (record["source_row_id"], record["generation_model"], record["retrieval_settings_digest"])
        pairs.setdefault(group, {})[record["system"]] = record
    comparison = []
    for (row_id, model, _), systems in pairs.items():
        if set(systems) != set(SYSTEMS):
            continue
        base, adk = systems["baseline"], systems["adk"]
        seen = [[chunk["id"] for chunk in record["retrieved_chunks"]] for record in (base, adk)]
        if not seen[0] or not seen[1]:
            result = "not_comparable"
        elif base["retrieval_query"] == adk["retrieval_query"] and base["top_k"] == adk["top_k"] and seen[0] == seen[1]:
            result = "match"
        else:
            result = "mismatch"
        comparison.append({"source_row_id": row_id, "generation_model": model, "result": result,
                           "baseline_chunk_ids": seen[0], "adk_chunk_ids": seen[1]})
    return comparison


def stop_code(record):
    error = record.get("error") or {}
    if error.get("service_code") in STOP_CODES:
        return error["service_code"]
    found = re.search(r"service code (\d+)", error.get("message") or "")
    if found and int(found.group(1)) in STOP_CODES:
        return int(found.group(1))
    return None


def load_results(output):
    if not output.exists():
        return {"schema_version": SCHEMA_VERSION, "records": []}
    state = json.loads(output.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION or not isinstance(state.get("records"), list):
        raise ValueError(f"{output} is not a results file from this runner. Use a new output path.")
    return state


def run_comparison(plan, systems, backend, output, *, limit=None, retry_errors=False):
    """Run what is still needed, saving after every call."""
    state = load_results(output)
    positions = {record["record_key"]: index for index, record in enumerate(state["records"])}
    calls, stopped = 0, False
    for row_id in plan["source_row_ids"]:
        for system in systems:
            if stopped or (limit is not None and calls >= limit):
                break
            settings, _ = build_settings(backend, plan, system)
            key = record_key(row_id, system, backend.model, digest(settings))
            previous = state["records"][positions[key]] if key in positions else None
            if previous and (previous["status"] not in RETRYABLE or not retry_errors):
                note = "already done" if previous["status"] not in RETRYABLE else "failed; use --retry-errors"
                print(f"skip row {row_id} {system}: {previous['status']} ({note})")
                continue
            record = attempt_once(backend, plan, system, row_id, output, previous)
            calls += 1
            if key in positions:
                state["records"][positions[key]] = record
            else:
                positions[key] = len(state["records"])
                state["records"].append(record)
            state["retrieval_comparison"] = compare_retrieval(state["records"])
            write_json(output, state)
            print(f"row {row_id} {system} attempt {record['attempt']}: {record['status']} "
                  f"({record['elapsed_seconds']}s)")
            code = stop_code(record)
            if code:
                print(f"Stopped after service code {code}; saved records are intact.")
                stopped = True
    print_summary(state)
    return state


def print_summary(state):
    counts = Counter((record["system"], record["status"]) for record in state["records"])
    for (system, status), count in sorted(counts.items()):
        print(f"{system}: {status} = {count}")
    outcomes = Counter(entry["result"] for entry in state.get("retrieval_comparison", []))
    if outcomes:
        print("retrieval pairs: " + ", ".join(f"{name} = {count}" for name, count in sorted(outcomes.items())))


def export_scoring_input(results_path, key_facts_directory, output, *, directory=DEFAULT_DIRECTORY):
    """Convert saved records to the input score_outputs.py expects, including every failure."""
    state = load_results(Path(results_path))
    if not state["records"]:
        raise ValueError(f"No saved records in {results_path}.")
    reports = {int(row["source_row_id"]): row["transcription"]
               for row in read_csv(Path(directory) / "mtsamples_curated_50.csv")}
    jobs, seen = [], set()
    for record in state["records"]:
        if record["mode"] != "live":
            raise ValueError("Offline records are scripted and must not be scored.")
        identity = (record["case_id"], record["system"], record["generation_model"])
        if identity in seen:
            raise ValueError(f"{identity} has results under more than one group of settings. "
                             "Keep each settings change in its own results file before scoring.")
        seen.add(identity)
        row_id = record["source_row_id"]
        report = reports[row_id]
        if digest(report) != record["source_digest"]:
            raise ValueError(f"Source row {row_id} differs from the text that was generated from.")
        facts = json.loads((Path(key_facts_directory) / f"source_row_{row_id}.json").read_text(encoding="utf-8"))
        if facts["source_report"] != report:
            raise ValueError(f"The key facts for source row {row_id} were prepared from different text.")
        validate_key_facts(report, facts["key_facts"])
        jobs.append({"case_id": record["case_id"], "system": record["system"],
                     "generation_model": record["generation_model"],
                     "output_kind": "draft" if record["output_kind"] == "needs_review_draft" else "final",
                     "run_status": record["status"], "source_report": report, "key_facts": facts["key_facts"],
                     "retrieved_context": [{"id": chunk["id"], "text": chunk["text"]}
                                           for chunk in record["retrieved_chunks"]],
                     "output": record["output_text"], "source_row_id": row_id,
                     "frozen_set_version": record["frozen_set_version"],
                     "generation_run_id": record["record_key"],
                     "generation_prompt_version": record["prompt_version"],
                     "retrieval_snapshot": record["settings"]["retrieval_index"]})
    write_json(Path(output), {"records": jobs})
    print(f"Saved {len(jobs)} scoring inputs to {output}")


def default_output(ids_path, offline):
    plan = json.loads(Path(ids_path).read_text(encoding="utf-8"))
    suffix = "-offline" if offline else ""
    return RESULTS_DIRECTORY / f"{plan['pilot_version']}{suffix}.json"


def run_live(plan, systems, model, output, limit, retry_errors):
    from google import genai
    from retrieval.gemini_chroma import api_key

    index_target, index = open_live_index()
    if "adk" in systems:
        check_adk_settings(model)
    with genai.Client(api_key=api_key()) as client:
        backend = live_backend(client, model, index_target, index)
        return run_comparison(plan, systems, backend, output, limit=limit, retry_errors=retry_errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", type=Path, default=DEFAULT_IDS, help="JSON file listing the reports to run.")
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Generation model for both systems.")
    parser.add_argument("--output", type=Path,
                        help="Results file. Default: data/comparison_results/<pilot_version>.json")
    parser.add_argument("--limit", type=int, help="Maximum generation calls this run.")
    parser.add_argument("--retry-errors", action="store_true", help="Run failed records again.")
    parser.add_argument("--offline", action="store_true", help="Use scripted responses; no API calls.")
    parser.add_argument("--export-scoring", type=Path, metavar="PATH",
                        help="Do not generate. Convert saved results to score_outputs.py input at PATH.")
    parser.add_argument("--key-facts-dir", type=Path,
                        help="With --export-scoring: folder of source_row_<id>.json key-fact files.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")
    if bool(args.export_scoring) != bool(args.key_facts_dir):
        parser.error("--export-scoring and --key-facts-dir must be used together.")
    try:
        output = args.output or default_output(args.ids, args.offline)
        if args.export_scoring:
            export_scoring_input(output, args.key_facts_dir, args.export_scoring)
            return
        plan = load_plan(args.ids)
        systems = list(dict.fromkeys(args.systems))
        if args.offline:
            run_comparison(plan, systems, offline_backend(), output,
                           limit=args.limit, retry_errors=args.retry_errors)
        else:
            run_live(plan, systems, args.model, output, args.limit, args.retry_errors)
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        parser.exit(1, f"Comparison stopped: {type(exc).__name__}: {exc}\n")
    print(f"Results: {output}")


if __name__ == "__main__":
    main()
