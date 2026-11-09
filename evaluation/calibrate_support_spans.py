"""Development judge using numbered source spans instead of generated quotations."""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import calibrate_support_v2 as previous
from .score_outputs import write_json
from .scoring import digest, generation_schema, safe_error

VERSION = "document-support-spans-2026-11-07-v4"
SPAN_VERSION = "lossless-sentence-blocks-v1"
PROMPT = previous.PROMPT.replace(
    "exact evidence_quote for supported\nor contradicted status",
    "evidence_span_ids for supported or contradicted status")
PROMPT = PROMPT.replace(
    "A quote must substantively support the\nspecific proposition, not just share its subject. If support depends on adjacent text,\nquote a continuous span that includes the relevant context.",
    "Selected source spans must substantively support the specific proposition, not just\nshare its subject. If support depends on adjacent text, select all necessary span IDs.")
PROMPT += """\nEvidence is supplied as ordered evidence_spans, each with an id and exact text.
Use only the supplied IDs in evidence_span_ids; never create IDs or copy source quotes.
Supported and contradicted propositions need at least one ID. For not_established,
use [] unless specific evidence helps explain the absence or limitation. Read spans in
order and keep neighboring context. Splits are mechanical, not semantic judgments.
Return sentence_quote verbatim from the answer sentence as before. Python will retrieve
the source text for selected IDs. Selecting a valid ID does not establish support.
"""


class SpanProposition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposition: str = Field(min_length=1)
    sentence_quote: str = Field(min_length=1)
    status: Literal["supported", "contradicted", "not_established"]
    evidence_span_ids: list[str]
    reason: str = Field(min_length=1)


class SpanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    propositions: list[SpanProposition] = Field(min_length=1)
    complete_sentence_supported: bool
    citation_support: bool | None
    citation_reason: str = Field(min_length=1)


def source_spans(text):
    """Keep every source character and offset, including whitespace; never paraphrase."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Nonblank source text is required.")
    # Delimiters stay at the end of the previous span. Abbreviation splits are harmless:
    # all ordered text is retained and adjacent IDs can be selected together.
    boundaries = [m.end() for m in re.finditer(r"(?<=[.!?])[ \t\r\n]+(?=[A-Z0-9])|(?:\r?\n){2,}", text)]
    spans, start = [], 0
    for end in sorted(set(boundaries + [len(text)])):
        if end <= start:
            continue
        if not text[start:end].strip():
            continue
        spans.append({"id": f"E{len(spans) + 1:03d}", "start": start, "end": end,
                      "text": text[start:end]})
        start = end
    if start < len(text):
        spans[-1]["text"] += text[start:]
        spans[-1]["end"] = len(text)
    assert "".join(s["text"] for s in spans) == text
    return spans


def prepare_suite(suite):
    if suite.get("suite_version") != previous.VERSION or suite.get("run_kind") != "development_only":
        raise ValueError("Expected the v2 development source suite.")
    dev, held = (set(suite["question_groups"][k]) for k in ("development", "heldout"))
    if dev & held or any(c["question_id"] not in dev for c in suite["cases"]):
        raise ValueError("Only separated development questions are allowed.")
    cases = []
    for case in suite["cases"]:
        updated = dict(case)
        if case["context_status"] == "ready":
            previous.judge_payload(case)
            updated["source_spans"] = source_spans(case["evidence"])
            updated["source_spans_digest"] = digest(updated["source_spans"])
        cases.append(updated)
    return {**suite, "suite_version": VERSION, "source_suite_digest": digest(suite),
            "span_version": SPAN_VERSION, "cases": cases}


def judge_payload(case):
    previous.judge_payload(case)
    spans = case.get("source_spans")
    if spans != source_spans(case["evidence"]) or case.get("source_spans_digest") != digest(spans):
        raise previous.DiagnosticError("source_spans_invalid", "input_validation")
    return {"question": case["question"], "sentence": case["sentence"],
            "evidence_spans": [{"id": s["id"], "text": s["text"]} for s in spans]}


def validate_decision(case, decision):
    judge_payload(case)
    try:
        parsed = SpanDecision.model_validate(decision).model_dump()
    except ValidationError as exc:
        raise previous.DiagnosticError("response_schema_invalid", "response_validation") from exc
    spans = {s["id"]: s for s in case["source_spans"]}
    restored, local = [], []
    for proposition in parsed["propositions"]:
        ids = proposition["evidence_span_ids"]
        if len(ids) != len(set(ids)):
            raise previous.DiagnosticError("evidence_span_ids_repeated", "response_validation")
        if any(ident not in spans for ident in ids):
            raise previous.DiagnosticError("evidence_span_id_unknown", "response_validation")
        if proposition["status"] in {"supported", "contradicted"} and not ids:
            raise previous.DiagnosticError("evidence_span_ids_missing", "response_validation")
        anchors = sorted((spans[ident] for ident in ids), key=lambda s: s["start"])
        item = {k: v for k, v in proposition.items() if k != "evidence_span_ids"}
        # Reuse the earlier local checks for sentence quotes, required reasons and
        # coverage consistency; every retrieved anchor has already been source-checked.
        local.append({**item, "evidence_quote": anchors[0]["text"] if anchors else ""})
        restored.append({**proposition, "evidence_spans": anchors})
    previous.validate_decision(case, {**parsed, "propositions": local})
    return {**parsed, "propositions": restored}


def judge(case, *, model):
    from google.genai import types
    from faithfulmed_demo.config import model_client, require_text
    with model_client() as client:
        response = client.models.generate_content(model=model, contents=json.dumps(judge_payload(case)),
            config=types.GenerateContentConfig(system_instruction=PROMPT, temperature=0,
                response_mime_type="application/json", response_schema=generation_schema(SpanDecision)))
    try:
        text = require_text(response)
    except ValueError as exc:
        raise previous.DiagnosticError("response_incomplete_or_empty", "response_extraction") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise previous.DiagnosticError("response_invalid_json", "response_parsing") from exc


def run_suite(suite, output, *, model, limit=6, retry_errors=False, judge_fn=judge):
    if suite.get("suite_version") != VERSION or suite.get("span_version") != SPAN_VERSION or suite.get("run_kind") != "development_only":
        raise ValueError("Expected the v4 development span suite.")
    dev, held = (set(suite["question_groups"][k]) for k in ("development", "heldout"))
    if dev & held or any(c["question_id"] not in dev for c in suite["cases"]):
        raise ValueError("Only development questions are allowed.")
    if limit < 1:
        raise ValueError("limit must be positive.")
    signature = digest({"suite": suite, "prompt": PROMPT, "schema": generation_schema(SpanDecision),
                        "version": VERSION, "model": model, "temperature": 0})
    state = {"run_digest": signature, "suite_version": VERSION, "span_version": SPAN_VERSION,
             "prompt_digest": digest(PROMPT), "schema_digest": digest(generation_schema(SpanDecision)),
             "model": model, "temperature": 0, "records": []}
    output = Path(output)
    if output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
        if state.get("run_digest") != signature:
            raise ValueError("Existing result uses a different suite/model/prompt/schema.")
    latest = {r["case_id"]: r for r in state["records"]}
    cases = [c for c in suite["cases"] if c["context_status"] == "ready" and c["reference_status"] == "eligible"
             and (c["case_id"] not in latest or (retry_errors and latest[c["case_id"]]["status"] != "ok"))]
    for case in cases[:limit]:
        started, stage = time.perf_counter(), "input_validation"
        result = {"case_id": case["case_id"], "question_id": case["question_id"]}
        try:
            judge_payload(case)
            stage = "service_call_or_response"
            response = judge_fn(case, model=model)
            stage = "response_validation"
            result.update(validate_decision(case, response), status="ok")
        except previous.DiagnosticError as exc:
            result.update(status="error", error_type="DiagnosticError", error_category=exc.category, error_stage=exc.stage)
        except Exception as exc:
            result.update(status="error", error_category="input_invalid" if stage == "input_validation" else "unclassified_error",
                          error_stage=stage, **safe_error(exc))
        result["seconds"] = round(time.perf_counter() - started, 3)
        state["records"].append(result)
        state["summary"] = previous.summarize(suite["cases"], state["records"])
        write_json(output, state)
        print(f"Attempted {state['summary']['attempted_cases']} development cases: {result['status']}")
        if result.get("service_code") in {400, 401, 403, 404, 429}:
            break
    if not output.exists():
        state["summary"] = previous.summarize(suite["cases"], state["records"])
        write_json(output, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("prepare", "run"):
        command = sub.add_parser(action)
        command.add_argument("--suite", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if action == "run":
            command.add_argument("--model", required=True)
            command.add_argument("--limit", type=int, default=6)
            command.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    try:
        suite = json.loads(args.suite.read_text(encoding="utf-8"))
        if args.action == "prepare":
            if args.output.exists():
                raise ValueError("Suite exists; choose a new version/path.")
            result = prepare_suite(suite)
            write_json(args.output, result)
            print(json.dumps(result["counts"], indent=2))
        else:
            result = run_suite(suite, args.output, model=args.model, limit=args.limit, retry_errors=args.retry_errors)
            print(json.dumps(result["summary"], indent=2))
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
