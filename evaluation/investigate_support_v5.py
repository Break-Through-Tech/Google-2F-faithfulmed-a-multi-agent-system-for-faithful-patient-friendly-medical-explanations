"""Export the v5 disagreements and their original reference evidence, without API calls."""

import hashlib
import json
from pathlib import Path

from .audit_support_references import identity
from .scoring import digest


def main():
    root = Path("data/calibration_results")
    paths = {
        "dataset": Path("data/MedAESQA_data/medaesqa_v1.json"),
        "suite": root / "medaesqa_document_development_v4_spans.json",
        "run": root / "document_support_v5_development.json",
        "previous_run": root / "document_support_v3_development.json",
    }
    data = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in paths.items()}
    cases = {c["case_id"]: c for c in data["suite"]["cases"]}
    questions = {q["question_id"]: q for q in data["dataset"]}
    records = data["run"]["records"]
    assert len(records) == len({r["case_id"] for r in records}) == 26
    assert all(r["status"] == "ok" for r in records)
    assert all(cases[r["case_id"]]["reference_status"] == "eligible" for r in records)
    findings = []
    for result in records:
        case = cases[result["case_id"]]
        if result["citation_support"] == case["reference_support"]:
            continue
        references = []
        for location in case["reference_records"]:
            sentences = questions[case["question_id"]]["machine_generated_answers"][location["answer_model"]]["answer_sentences"]
            index = next(i for i, s in enumerate(sentences) if str(s["answer_sentence_id"]) == str(location["sentence_id"]))
            sentence = sentences[index]
            citation = sentence["citation_assessment"][location["citation_index"]]
            assert identity(case["question_id"], citation["cited_pmid"], sentence["answer_sentence"]) == identity(case["question_id"], case["cited_pmid"], case["sentence"])
            assert citation["evidence_relation"].strip().lower() == case["reference_relation"]
            references.append({**location, "original_sentence": sentence["answer_sentence"],
                "preceding_sentence": sentences[index - 1]["answer_sentence"] if index else None,
                "original_citation": citation})
        findings.append({"case": case, "judge_output": result, "original_records": references})
    previous = {r["case_id"]: r for r in data["previous_run"]["records"]}
    matched = [(previous[r["case_id"]], r) for r in records
               if r["case_id"] in previous and previous[r["case_id"]]["status"] == "ok"]
    comparison = {"matched_cases": len(matched),
        "v3_correct": sum(a["citation_support"] == cases[a["case_id"]]["reference_support"] for a, b in matched),
        "v5_correct": sum(b["citation_support"] == cases[b["case_id"]]["reference_support"] for a, b in matched)}
    output = {"kind": "offline_development_failure_investigation", "api_calls": 0,
        "source_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()},
        "run_digest": data["run"]["run_digest"], "comparison": comparison,
        "failures": findings, "failure_count": len(findings),
        "all_supported_diagnostic_correct": sum(r["complete_sentence_supported"] == cases[r["case_id"]]["reference_support"] for r in records),
        "any_supported_diagnostic_correct": sum(any(p["status"] == "supported" for p in r["propositions"]) == cases[r["case_id"]]["reference_support"] for r in records),
        "note": "Diagnostic transformations of saved outputs, not new model scores or replacement labels. No held-out cases reviewed."}
    assert len(findings) == 13
    target = root / "document_support_v5_investigation.json"
    if target.exists() and digest(json.loads(target.read_text(encoding="utf-8"))) != digest(output):
        raise ValueError("Existing investigation differs; preserve it and use a new version.")
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"failure_count": len(findings), **comparison, "output": str(target)}))


if __name__ == "__main__":
    main()
