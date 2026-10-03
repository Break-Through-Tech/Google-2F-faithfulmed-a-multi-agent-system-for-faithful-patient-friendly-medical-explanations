"""Alicia's September readability scorer, extended for local and batch use.

The starter medical vocabulary and original metric fields are retained.
Refusal and sentence detection are transparent English-language heuristics.
"""
import math
import re

import pandas as pd
import textstat

MEDICAL_TERMS = {
    "diagnosis", "prognosis", "symptom", "symptoms", "treatment",
    "medication", "medications", "therapy", "therapeutic",
    "clinical", "chronic", "acute", "inflammation", "infection",
    "syndrome", "disease", "disorder", "anatomy", "physiology",
    "biopsy", "screening", "contraindication", "adverse",
    "intravenous", "antibiotic", "anticoagulant", "hypertension",
    "diabetes", "cardiovascular", "neurological",
}
REFUSAL_PATTERN = re.compile(
    r"\b(?:i|we)\s+(?:cannot|can't|am unable to|are unable to|won't|will not)"
    r"\s+(?:help|assist|provide|answer|explain|interpret|process|comply)\b",
    re.I,
)


def count_sentences(text):
    """Protect decimals/common abbreviations before splitting punctuation/newlines."""
    protected = re.sub(r"(?<=\d)\.(?=\d)", "<DOT>", text)
    protected = re.sub(
        r"\b(?:Dr|Mr|Mrs|Ms|Prof|vs|e\.g|i\.e)\.",
        lambda m: m[0].replace(".", "<DOT>"), protected, flags=re.I,
    )
    return sum(bool(re.search(r"[A-Za-z]", part))
               for part in re.split(r"[.!?]+|\n+", protected))


def evaluate_readability(text, max_grade=8, max_words=None):
    """Score one explanation; refusals get metrics but cannot pass readability."""
    if not isinstance(text, str) or not text.strip():
        return {"status": "error", "error": "Text is empty or invalid.",
                "is_refusal": None, "passes_readability": False}
    clean_text = " ".join(text.split())
    words = re.findall(r"\b[a-zA-Z]+(?:['â€™-][a-zA-Z]+)*\b", clean_text.lower())
    if not words:
        return {"status": "error", "error": "Text contains no alphabetic words.",
                "is_refusal": None, "passes_readability": False}
    word_count = len(words)
    sentence_count = max(count_sentences(text), 1)
    jargon_words = sorted(set(words) & MEDICAL_TERMS)
    jargon_count = sum(word in MEDICAL_TERMS for word in words)
    # Use the corrected sentence count in BOTH formulas. textstat's internal
    # sentence counter otherwise still counts some abbreviations as boundaries.
    syllables = [textstat.syllable_count(word) for word in words]
    fk_grade = .39 * word_count / sentence_count + 11.8 * sum(syllables) / word_count - 15.59
    smog_grade = (1.043 * math.sqrt(30 * sum(s >= 3 for s in syllables) / sentence_count)
                  + 3.1291) if sentence_count >= 3 else None
    is_refusal = bool(REFUSAL_PATTERN.search(clean_text.replace("â€™", "'")))
    grade_pass = fk_grade <= max_grade
    length_pass = max_words is None or word_count <= max_words
    return {
        "status": "ok", "word_count": word_count, "sentence_count": sentence_count,
        "flesch_kincaid_grade": round(fk_grade, 2),
        "smog_grade": round(smog_grade, 2) if smog_grade is not None else None,
        "medical_jargon_count": jargon_count,
        "medical_jargon_density": round(jargon_count / word_count, 4),
        "medical_terms_found": ", ".join(jargon_words), "is_refusal": is_refusal,
        "passes_grade_target": grade_pass, "passes_length_target": length_pass,
        "passes_readability": grade_pass and length_pass and not is_refusal,
    }


def evaluate_outputs(records, max_grade=8, max_words=None):
    """Preserve baseline metadata/status; add metrics with an evaluation_ prefix."""
    if "model_output" not in records:
        raise ValueError("Input must contain a model_output column.")
    if any(str(c).startswith("evaluation_") for c in records.columns):
        raise ValueError("Input already contains evaluation_ columns; use original outputs.")
    metrics = []
    for row in records.to_dict("records"):
        if "status" in row and row["status"] != "ok":
            result = {"status": "skipped", "error": "Baseline status is not ok.",
                      "is_refusal": None, "passes_readability": False}
        else:
            result = evaluate_readability(row["model_output"], max_grade, max_words)
        metrics.append({"evaluation_" + k: v for k, v in result.items()})
    return pd.concat([records.reset_index(drop=True), pd.DataFrame(metrics)], axis=1)


def summarize_results(results):
    """Refusal denominator: valid text outputs with successful baseline status."""
    if results.empty:
        return {"total_rows": 0, "scored_outputs": 0, "refusals": 0,
                "refusal_rate": None, "skipped_rows": 0, "invalid_outputs": 0,
                "readability_pass_rate": None}
    scored = results.loc[results.evaluation_status.eq("ok")]
    n = len(scored)
    refusals = int(scored.evaluation_is_refusal.fillna(False).sum())
    return {
        "total_rows": len(results), "scored_outputs": n, "refusals": refusals,
        "refusal_rate": refusals / n if n else None,
        "skipped_rows": int(results.evaluation_status.eq("skipped").sum()),
        "invalid_outputs": int(results.evaluation_status.eq("error").sum()),
        "readability_pass_rate": float(scored.evaluation_passes_readability.mean()) if n else None,
    }
