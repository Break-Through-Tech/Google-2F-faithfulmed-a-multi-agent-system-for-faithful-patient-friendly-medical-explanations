"""Score saved final answers (or explicit drafts) without changing either system."""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from .scoring import (SCORING_VERSION, INSTRUCTION, assess_output, compute_metrics,
                      digest, prepare_key_facts, safe_error, summarize, validate_assessment)
from .readability import evaluate_readability

EXAMPLES = Path(__file__).parent / "examples/advisor_scoring_examples.json"
PROVENANCE = ("source_row_id", "frozen_set_version", "generation_run_id", "generation_prompt_version",
              "retrieval_snapshot")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    temporary.replace(path)


def advisor_jobs():
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    return [{"case_id": case["id"], "system": "advisor_example", "generation_model": "fixture",
             "source_report": data["source_report"], "key_facts": data["key_facts"],
             "retrieved_context": data["retrieved_context"], "output": case["output"],
             "output_kind": "final", "run_status": "complete",
             "reference_assessment": case["reference_assessment"]} for case in data["examples"]]


def public_job(job):
    """Never send reference annotations, expected scores, or model labels to the judge."""
    return {k: job[k] for k in ("source_report", "output", "key_facts", "retrieved_context")}


def run_job(job, *, model, reference=False):
    result = {k: job[k] for k in ("case_id", "system", "generation_model", "output_kind")}
    result.update({k: job[k] for k in PROVENANCE if k in job})
    result.update(scoring_version=SCORING_VERSION, judge_model=model if not reference else None,
                  scoring_mode="reference_fixture" if reference else "live_judge",
                  input_digest=digest(public_job(job)), output=job["output"])
    result.update(source_digest=digest(job["source_report"]), key_facts_digest=digest(job["key_facts"]),
                  context_digest=digest(job["retrieved_context"]))
    started = time.perf_counter()
    try:
        output = job["output"]
        if job.get("run_status", "complete") not in {"ok", "complete"} and job["output_kind"] == "final":
            return {**result, "status": "generation_failed", "generation_status": job["run_status"]}
        if not isinstance(output, str) or not output.strip():
            return {**result, "status": "empty_output"}
        readability = evaluate_readability(output)
        result["readability"] = readability
        if readability.get("status") != "ok":
            return {**result, "status": "invalid_text"}
        if readability.get("is_refusal"):
            return {**result, "status": "refusal"}
        if reference:
            assessment = validate_assessment(job["source_report"], output, job["key_facts"],
                                             job["retrieved_context"], job["reference_assessment"])
        else:
            assessment = assess_output(job["source_report"], output, job["key_facts"],
                                       job["retrieved_context"], model=model)
        metrics = compute_metrics(assessment)
        result.update(status="scored" if metrics["claims_total"] else "no_claims",
                      assessment=assessment.model_dump(), metrics=metrics)
    except Exception as exc:
        # Service exception strings can contain request details. Keep a safe error record.
        result.update(status="evaluation_failed", **safe_error(exc))
    finally:
        result["evaluation_seconds"] = round(time.perf_counter() - started, 3)
    return result


def run(jobs, output_path, *, model, reference=False, limit=None):
    if not jobs:
        raise ValueError("Input must contain at least one evaluation record.")
    identities, combinations = {}, set()
    for index, job in enumerate(jobs):
        job.setdefault("case_id", str(job.get("source_row_id", index)))
        job.setdefault("system", "unspecified")
        job.setdefault("generation_model", "unspecified")
        job.setdefault("output_kind", "final")
        job.setdefault("retrieved_context", [])
        if job["output_kind"] not in {"final", "draft"}:
            raise ValueError("output_kind must be final or draft.")
        for key in ("source_report", "key_facts", "output"):
            if key not in job:
                raise ValueError(f"Missing input field: {key}")
        identity = digest([job["source_report"], job["key_facts"]])
        if job["case_id"] in identities and identities[job["case_id"]] != identity:
            raise ValueError("The same case must use identical source text and key facts across systems/models.")
        identities[job["case_id"]] = identity
        combination = (job["case_id"], job["system"], job["generation_model"], job["output_kind"])
        if combination in combinations:
            raise ValueError("Repeated case/system/model/output-kind would duplicate the denominator.")
        combinations.add(combination)
    signature = digest(dict(jobs=[{**public_job(j), "case_id": j["case_id"],
                                  "system": j["system"], "generation_model": j["generation_model"],
                                  "output_kind": j["output_kind"], "run_status": j.get("run_status", "complete"),
                                  "provenance": {k: j[k] for k in PROVENANCE if k in j},
                                  "reference_assessment": j.get("reference_assessment") if reference else None}
                                 for j in jobs], judge_model=model, reference=reference,
                            scoring_version=SCORING_VERSION, instruction=INSTRUCTION))
    state = {"run_digest": signature, "scoring_version": SCORING_VERSION, "records": []}
    if output_path.exists():
        state = json.loads(output_path.read_text(encoding="utf-8"))
        if state.get("run_digest") != signature:
            raise ValueError("Existing result belongs to different inputs/settings. Use a new output path.")
    completed = len(state["records"])
    stop = len(jobs) if limit is None else min(len(jobs), completed + limit)
    for index in range(completed, stop):
        result = run_job(jobs[index], model=model, reference=reference)
        state["records"].append(result)
        groups = defaultdict(list)
        for record in state["records"]:
            groups[(record["system"], record["generation_model"])].append(record)
        state["summary_by_system_model"] = [
            {"system": system, "generation_model": generation_model, **summarize(records)}
            for (system, generation_model), records in groups.items()]
        state["requested_outputs"] = len(jobs)
        state["attempted_outputs"] = len(state["records"])
        write_json(output_path, state)
        print(f"{index + 1}/{len(jobs)}: {result['case_id']} -> {result['status']}")
        if result.get("service_code") in {400, 401, 403, 404, 429}:
            print("Stopped after a service access/quota error; saved records remain intact.")
            break
    return state


def main():
    from faithfulmed_demo.config import MODEL
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="JSON record, or an object with a records list.")
    source.add_argument("--advisor-examples", action="store_true")
    source.add_argument("--prepare-source", type=Path, help="Source-only JSON with source_report.")
    parser.add_argument("--live", action="store_true", help="Call Gemini for advisor examples; default uses reference fixtures.")
    parser.add_argument("--judge-model", default=MODEL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="Maximum new evaluations this invocation.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")
    if args.prepare_source:
        if args.output.exists():
            parser.error("Source fact inventory already exists; choose a new version/path.")
        data = json.loads(args.prepare_source.read_text(encoding="utf-8"))
        facts = prepare_key_facts(data["source_report"], model=args.judge_model)
        write_json(args.output, {"source_report": data["source_report"], "key_facts": facts,
                   "source_digest": digest(data["source_report"]), "model": args.judge_model,
                   "scoring_version": SCORING_VERSION})
        print(f"Saved {len(facts)} source-only key facts to {args.output}")
        return
    if args.advisor_examples:
        jobs = advisor_jobs()
    else:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        jobs = data if isinstance(data, list) else data["records"] if "records" in data else [data]
    try:
        state = run(jobs, args.output, model=args.judge_model,
                    reference=args.advisor_examples and not args.live, limit=args.limit)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(f"Saved {len(state['records'])} records to {args.output}")


if __name__ == "__main__":
    main()
