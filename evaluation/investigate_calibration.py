"""Controlled context check on previously attempted development cases only."""

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

from .scoring import digest
from .score_outputs import write_json

CONTEXT_VERSION = "pubmed-title-abstract-diagnostic-v2"


def normalized_statement(text):
    from .calibrate_verifier import clean_sentence
    return re.sub(r"\W+", " ", clean_sentence(text).casefold()).strip()


def audit_document_labels(data, cases):
    """Report document-level reference conflicts; never resolve or exclude them."""
    results = []
    for case in cases:
        matches = []
        for question in data:
            if question["question_id"] != case["question_id"]:
                continue
            for answer_model, answer in question["machine_generated_answers"].items():
                for sentence in answer["answer_sentences"] or []:
                    if normalized_statement(sentence["answer_sentence"]) != normalized_statement(case["sentence"]):
                        continue
                    for citation in sentence["citation_assessment"] or []:
                        if str(citation["cited_pmid"]) == str(case["cited_pmid"]):
                            text = citation["evidence_support"]
                            matches.append({"answer_model": answer_model,
                                "sentence_id": sentence["answer_sentence_id"],
                                "relation": citation["evidence_relation"],
                                "has_excerpt": isinstance(text, str) and bool(text.strip()),
                                "excerpt_digest": digest(text)})
        eligible = [r for r in matches if r["has_excerpt"]
                    and r["relation"] in {"supporting", "neutral", "contradicting"}]
        results.append({"case_id": case["case_id"], "question_id": case["question_id"],
            "pmid": case["cited_pmid"], "matching_record_count": len(matches),
            "relation_counts": dict(Counter(r["relation"] for r in matches)),
            "mixed_document_relations": len({r["relation"] for r in matches}) > 1,
            "binary_conflict_with_nonblank_excerpts": len({r["relation"] == "supporting" for r in eligible}) > 1,
            "records": matches})
    return results


def pilot_cases(suite, run):
    if run["split"] != "development":
        raise ValueError("Context investigation is restricted to development predictions.")
    by_id = {case["case_id"]: case for case in suite["splits"]["development"]}
    ids = list(dict.fromkeys(record["case_id"] for record in run["records"]))
    if not ids or any(ident not in by_id for ident in ids):
        raise ValueError("Pilot contains missing or non-development cases.")
    return [by_id[ident] for ident in ids]


def parse_pubmed(xml):
    records = {}
    for article in ET.fromstring(xml).findall(".//PubmedArticle"):
        citation = article.find("MedlineCitation")
        pmid = citation.findtext("PMID", "").strip()
        node = citation.find("Article")
        if node is None or not pmid:
            continue
        title_node = node.find("ArticleTitle")
        title = " ".join("".join(title_node.itertext()).split()) if title_node is not None else ""
        paragraphs = []
        for paragraph in node.findall("Abstract/AbstractText"):
            text = " ".join("".join(paragraph.itertext()).split())
            label = paragraph.get("Label")
            if text:
                paragraphs.append((label + ": " if label else "") + text)
        abstract = "\n".join(paragraphs)
        records[pmid] = {"pmid": pmid, "title": title, "abstract": abstract,
                         "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                         "context_sha256": digest([title, abstract])}
    return records


def fetch_context(cases):
    pmids = sorted({str(case["cited_pmid"]) for case in cases})
    if any(not re.fullmatch(r"[0-9]+", pmid) for pmid in pmids):
        raise ValueError("Only numeric PMIDs may be sent to the public document service.")
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    request = urllib.request.Request(url, headers={"User-Agent": "FaithfulMed-calibration-context-check/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        xml = response.read()
    records = parse_pubmed(xml)
    if set(records) != set(pmids):
        raise ValueError("PubMed returned missing or unexpected IDs; no partial context suite created.")
    if any(not r["abstract"].strip() for r in records.values()):
        raise ValueError("A selected document lacks an abstract; do not silently substitute a snippet.")
    return {"context_version": CONTEXT_VERSION, "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "request_url": url, "xml_sha256": hashlib.sha256(xml).hexdigest(), "records": records}


def enrich_pilot(suite, run, cache):
    original = pilot_cases(suite, run)
    enriched = []
    for case in original:
        pmid = str(case["cited_pmid"])
        document = cache["records"].get(pmid)
        if not document or str(document["pmid"]) != pmid:
            raise ValueError("Context PMID does not match a pilot citation.")
        if not document["title"].strip() or not document["abstract"].strip():
            raise ValueError("Every diagnostic case needs a title and abstract.")
        if document["context_sha256"] != digest([document["title"], document["abstract"]]):
            raise ValueError("Cached title/abstract changed after collection.")
        evidence = document["title"] + "\n\n" + document["abstract"]
        normalize = lambda text: " ".join(text.casefold().split())
        enriched.append({**case, "original_evidence": case["evidence"], "evidence": evidence,
            "evidence_scope": "pubmed_title_and_abstract", "context_source_url": document["source_url"],
            "context_sha256": document["context_sha256"],
            "original_snippet_found_in_abstract": normalize(case["evidence"]) in normalize(document["abstract"])})
    return {"suite_version": CONTEXT_VERSION, "run_kind": "development_context_diagnostic",
            "scope": "Same attempted development pairs and labels, using public PubMed title/abstract context. Not a held-out calibration result.",
            "source_suite_digest": digest(suite), "source_run_digest": run["run_digest"],
            "context_cache_digest": digest(cache), "dataset_sha256": suite["dataset_sha256"],
            "question_groups": {"development": sorted({c["question_id"] for c in enriched}),
                                "heldout": suite["question_groups"]["heldout"]},
            "splits": {"development": enriched, "heldout": []}}


def compare_runs(before, after):
    original = {r["case_id"]: r for r in before["records"]}
    updated = {r["case_id"]: r for r in after["records"]}
    if set(original) != set(updated):
        raise ValueError("A context comparison needs the exact same case IDs.")
    return [{"case_id": ident, "question_id": original[ident]["question_id"],
             "before_status": original[ident]["status"], "after_status": updated[ident]["status"],
             "before_support": original[ident].get("supports_sentence"),
             "after_support": updated[ident].get("supports_sentence")}
            for ident in original]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Diagnostic suite already exists; use a new version/path.")
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    run = json.loads(args.pilot.read_text(encoding="utf-8"))
    cases = pilot_cases(suite, run)
    if args.cache.exists():
        cache = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        cache = fetch_context(cases)
        write_json(args.cache, cache)
    result = enrich_pilot(suite, run, cache)
    write_json(args.output, result)
    print(json.dumps({"version": CONTEXT_VERSION, "cases": len(cases),
        "pmids": [c["cited_pmid"] for c in cases],
        "snippets_found": sum(c["original_snippet_found_in_abstract"] for c in result["splits"]["development"]),
        "heldout_cases_added": 0}, indent=2))


if __name__ == "__main__":
    main()
