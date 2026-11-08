"""Bounded pilot scoring retries with auditable restoration of formatting-only quotes."""

import argparse
import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from . import scoring
from .score_outputs import public_job, run_job, write_json

POLICY = "unique-markdown-whitespace-anchors-v1"


def canonical(text):
    chars, offsets = [], []
    # Preserve letters, punctuation, case, and numbers. Remove only inline Markdown
    # delimiters; retain single asterisks (e.g. multiplication) and all other symbols.
    removed = {i for m in re.finditer(r"\*\*|__|`", text) for i in range(m.start(), m.end())}
    for i, char in enumerate(text):
        if i in removed:
            continue
        if char.isspace():
            if chars and chars[-1] != " ":
                chars.append(" ")
                offsets.append(i)
        else:
            chars.append(char)
            offsets.append(i)
    if chars and chars[-1] == " ":
        chars.pop()
        offsets.pop()
    return "".join(chars), offsets


def restore_quote(quote, source):
    if quote in source:
        return quote
    needle, _ = canonical(quote)
    haystack, positions = canonical(source)
    matches = [m.start() for m in re.finditer(re.escape(needle), haystack)] if needle else []
    if len(matches) != 1:
        raise ValueError("Quote has no unique formatting-only source match.")
    start = matches[0]
    restored = source[positions[start]:positions[start + len(needle) - 1] + 1]
    assert canonical(restored)[0] == needle
    return restored


def restore_assessment(assessment, source, output, context):
    original = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment
    restored, changes = copy.deepcopy(original), []
    passages = {str(p["id"]): p["text"] for p in context}
    for claim in restored["claims"]:
        before = claim["output_quote"]
        claim["output_quote"] = restore_quote(before, output)
        if before != claim["output_quote"]:
            changes.append({"claim_id": claim["id"], "field": "output_quote", "original": before, "restored": claim["output_quote"]})
        for evidence in claim["evidence"]:
            text = source if evidence["origin"] == "report" else passages.get(evidence["context_id"])
            if text is None:
                raise ValueError("Unknown evidence source.")
            before = evidence["quote"]
            evidence["quote"] = restore_quote(before, text)
            if before != evidence["quote"]:
                changes.append({"claim_id": claim["id"], "field": "evidence_quote", "original": before, "restored": evidence["quote"]})
    return original, restored, changes


def run(inputs, initial, output, model):
    jobs = json.loads(inputs.read_text(encoding="utf-8"))["records"]
    first = json.loads(initial.read_text(encoding="utf-8"))
    assert len(jobs) == len(first["records"]) == 10
    signature = scoring.digest({"jobs": jobs, "initial": first, "model": model,
                                "policy": POLICY, "instruction": scoring.INSTRUCTION})
    state = {"run_digest": signature, "anchor_policy": POLICY, "records": [],
             "note": "Provisional clinical judgments. Successful first attempts reused; one retry per failed assessment."}
    if output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
        if state["run_digest"] != signature:
            raise ValueError("Changed pilot scoring inputs; use a new version.")
    validate = scoring.validate_assessment
    for i in range(len(state["records"]), len(jobs)):
        job, prior = jobs[i], first["records"][i]
        assert (prior["case_id"], prior["system"], prior["input_digest"]) == (job["case_id"], job["system"], scoring.digest(public_job(job)))
        if prior["status"] != "evaluation_failed":
            result = {**prior, "reused_initial_assessment": True}
        else:
            capture = {}

            def checked(source, answer, facts, context, assessment):
                capture["original_assessment"] = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment
                _, restored, changes = restore_assessment(assessment, source, answer, context)
                capture["anchor_changes"] = changes
                capture["restored_assessment"] = restored
                return validate(source, answer, facts, context, restored)

            with patch("evaluation.scoring.validate_assessment", side_effect=checked):
                result = run_job(job, model=model)
            result["previous_attempt"] = prior
            sidecar = output.parent / "assessment_attempts" / f"{i:02d}-{job['case_id']}-{job['system']}.json"
            write_json(sidecar, capture)
            result["assessment_audit_path"] = sidecar.relative_to(output.parent).as_posix()
            result["formatting_anchors_restored"] = len(capture.get("anchor_changes", []))
        state["records"].append(result)
        groups = defaultdict(list)
        for record in state["records"]:
            groups[record["system"]].append(record)
        state["summary_by_system"] = [{"system": k, **scoring.summarize(v)} for k, v in groups.items()]
        write_json(output, state)
        print(f"{i + 1}/10 {job['case_id']} {job['system']}: {result['status']}", flush=True)
        if result.get("service_code") in {400, 401, 403, 404, 429}:
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "initial", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--model", default="gemini-3.8-flash")
    args = parser.parse_args()
    run(args.input, args.initial, args.output, args.model)


if __name__ == "__main__":
    main()
