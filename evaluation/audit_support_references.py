"""Offline reference audit. Never reads predictions or calls a service."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .calibrate_verifier import clean_sentence
from .scoring import digest

POLICY = "support-conflict-2026-11-07-v1"
RELATIONS = {"supporting": True, "neutral": False, "contradicting": False, "not relevant": False}


def identity(question_id, pmid, sentence):
    statement = " ".join(clean_sentence(sentence).casefold().split())
    return (question_id, str(pmid).strip(), statement)


def audit(dataset, suite, cache):
    groups = defaultdict(list)
    loose = defaultdict(set)
    for question in dataset:
        for model, answer in question["machine_generated_answers"].items():
            for sentence in answer["answer_sentences"] or []:
                for index, citation in enumerate(sentence["citation_assessment"] or []):
                    key = identity(question["question_id"], citation["cited_pmid"], sentence["answer_sentence"])
                    groups[key].append(dict(answer_model=model, sentence_id=sentence["answer_sentence_id"],
                        citation_index=index, relation=citation["evidence_relation"].strip().lower(),
                        has_excerpt=bool((citation["evidence_support"] or "").strip())))
                    loose[(key[0], key[1], re.sub(r"\W+", " ", key[2]).strip())].add(key)
    summaries, cases = {}, []
    for split, selected in suite["splits"].items():
        seen, counts = set(), Counter()
        for case in selected:
            key = identity(case["question_id"], case["cited_pmid"], case["sentence"])
            records = groups[key]
            relations = Counter(r["relation"] for r in records)
            labels = {RELATIONS[r] for r in relations if r in RELATIONS}
            conflict = len(labels) > 1
            validity = not records or any(r not in RELATIONS for r in relations)
            duplicate = key in seen
            seen.add(key)
            doc = cache.get("records", {}).get(key[1])
            context = bool(doc and str(doc.get("pmid")) == key[1] and doc.get("title", "").strip()
                and doc.get("abstract", "").strip()
                and doc.get("context_sha256") == digest([doc["title"], doc["abstract"]]))
            neighbors = len(loose[(key[0], key[1], re.sub(r"\W+", " ", key[2]).strip())]) > 1
            reasons = []
            if conflict: reasons.append("conflicting_binary_references")
            if validity: reasons.append("invalid_or_unmapped_reference")
            if duplicate: reasons.append("duplicate_document_assertion")
            if neighbors: reasons.append("punctuation_neighbor_requires_review")
            if not context: reasons.append("title_abstract_not_cached")
            counts["selected"] += 1
            for reason in reasons: counts[reason] += 1
            if not reasons: counts["structurally_ready_not_semantically_validated"] += 1
            cases.append(dict(case_id=case["case_id"], split=split, question_id=key[0], pmid=key[1],
                identity_digest=digest(key), selected_reference=case["reference_relation"],
                relation_counts=dict(relations), binary_conflict=conflict,
                mixed_relations=len(relations)>1, cached_context=context,
                audit_flags=reasons, reference_records=records))
        summaries[split] = dict(counts)
    return dict(policy_version=POLICY, suite_digest=digest(suite), context_cache_digest=digest(cache),
                summaries=summaries, cases=cases, predictions_read=False, service_calls=0,
                note="Structural audit only. Held-out text is neither emitted nor semantically reviewed; original suite unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/MedAESQA_data/medaesqa_v1.json"))
    parser.add_argument("--suite", type=Path, default=Path("data/calibration_results/medaesqa_support_v1.json"))
    parser.add_argument("--cache", type=Path, default=Path("data/calibration_results/pubmed_pilot_context_v2.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Choose a new output path; existing audit will not be replaced.")
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))
    suite = read(args.suite)
    actual_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    if actual_hash != suite["dataset_sha256"]: parser.error("Dataset differs from the selected suite.")
    if set(suite["question_groups"]["development"]) & set(suite["question_groups"]["heldout"]):
        parser.error("Question splits overlap.")
    result = audit(read(args.dataset), suite, read(args.cache))
    result["dataset_sha256"] = actual_hash
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summaries"], indent=2))


if __name__ == "__main__":
    main()
