"""Reproduce the FaithfulMed 50-report source subset; no generation or annotation.

Run from the repository root: python EDAs/mtsamples_sampling.py (active medium set).
Use --profile mixed --output <another-directory> for historical mixed-length exports.
The notebook uses the same functions. Raw source text is never normalized in exports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from sklearn.feature_extraction.text import CountVectorizer

ROOT = Path(__file__).resolve().parents[1]
RANDOM_SEED = 42
MIN_WORDS = 40
NEAR_DUPLICATE_JACCARD = 0.85
LENGTH_TARGETS = {"short": 17, "medium": 17, "long": 16}
SPECIALTY_TARGETS = {
    "General Medicine": 4,
    "Cardiovascular / Pulmonary": 4,
    "Neurology": 4,
    "Gastroenterology": 3,
    "Orthopedic": 3,
    "Urology": 3,
    "Allergy / Immunology": 3,
    "Endocrinology": 3,
    "Hematology - Oncology": 3,
    "Emergency Room Reports": 4,
    "Discharge Summary": 4,
    "Surgery": 3,
    "Consult - History and Phy.": 3,
    "Radiology": 3,
    "SOAP / Chart / Progress Notes": 3,
}
SOURCE_FIELDS = ["medical_specialty", "sample_name", "description", "transcription", "keywords"]
# Presence cues for sampling only: no extraction of clinical facts or gold labels.
CONTENT_PATTERNS = {
    "diagnoses": r"\b(?:diagnos\w*|impression|assessment)\b",
    "symptoms": r"\b(?:symptoms?|complaints?|pain|dyspnea|nausea|cough|fever)\b",
    "medications": r"\b(?:medications?|medicines?|prescri\w*|\d+\s*mg|\d+\s*mcg)\b",
    "allergies": r"\b(?:allerg\w*|nkda)\b",
    "laboratory values": r"\b(?:laboratory|labs?|hemoglobin|hematocrit|creatinine|platelets?|wbc|bun|glucose)\b.{0,60}\d",
    "vital signs": r"\b(?:vital signs|blood pressure|pulse|heart rate|respiratory rate|temperature|saturation|bp)\b.{0,60}\d",
    "procedures": r"\b(?:procedures?|catheter\w*|biopsy|endoscopy|colonoscopy|intubat\w*)\b",
    "imaging": r"\b(?:imaging|x[ -]?rays?|mri|ct|ultrasound|radiograph\w*|echocardiogra\w*)\b",
    "past history": r"\b(?:past medical|past surgical|family history|social history|history of)\b",
    "treatment plans": r"\b(?:plan|treatment|recommend\w*|management)\b",
    "follow-up": r"\b(?:follow[ -]?up|return|appointment|recheck)\b",
    "surgery": r"\b(?:surgery|surgical|operative|operation|incision|resect\w*)\b",
    "assessment/plan": r"\b(?:assessment|impression)\b.*\bplan\b",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source(path: Path) -> pd.DataFrame:
    """Keep empty fields empty and preserve the original transcription strings."""
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, keep_default_na=False)
    elif path.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(path, keep_default_na=False, engine="openpyxl")
    else:
        raise ValueError("Source must be CSV or an openpyxl-compatible Excel file.")
    missing = set(SOURCE_FIELDS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required source columns: {sorted(missing)}")
    return frame


def blank_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.fillna("").astype(str).str.strip().eq("")


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def word_counts(frame: pd.DataFrame) -> pd.Series:
    # Whitespace-delimited words, matching the sampling EDA throughout.
    return frame.transcription.fillna("").str.split().str.len()


def source_eda(frame: pd.DataFrame) -> dict:
    missing = pd.DataFrame({"missing_count": [int(blank_mask(frame[c]).sum()) for c in frame]}, index=frame.columns)
    missing["missing_percent"] = missing.missing_count / len(frame) * 100
    nonempty = frame.loc[~blank_mask(frame.transcription), "transcription"]
    normalized = nonempty.map(normalize_text)
    return {
        "rows": len(frame),
        "columns": frame.columns.tolist(),
        "missing": missing,
        "duplicate_full_rows": int(frame.duplicated().sum()),
        "duplicate_rows_without_index": int(frame[SOURCE_FIELDS].duplicated().sum()),
        "duplicate_transcriptions": int(nonempty.duplicated().sum()),
        "duplicate_normalized_transcriptions": int(normalized.duplicated().sum()),
        "specialties": frame.medical_specialty.str.strip().replace("", "(missing)").value_counts(),
        "word_stats": word_counts(frame.loc[nonempty.index]).describe(percentiles=[.25, .5, .75]),
    }


def content_indicators(text: str) -> list[str]:
    return [name for name, pattern in CONTENT_PATTERNS.items() if re.search(pattern, text, re.I | re.S)]


def structure_indicator(row: pd.Series) -> str:
    text = row.transcription.lower()
    name = row.sample_name.lower()
    if (all(re.search(r"\b" + key + r"\s*:", text) for key in ("subjective", "objective", "assessment", "plan"))
            or ("soap" in name and "subjective" in text)
            or all(re.search(r"(?:^|[,\n])\s*" + key + r"\s*[-:]", text) for key in "soap")):
        return "SOAP-style"
    if "discharge" in name:
        return "discharge summary"
    if re.search(r"(?:^|[,\n])\s*(?:(?:pre|post)operative diagnos(?:is|es)|operative report|procedure performed)\s*:", text) or re.search(r"\b(?:operative report|procedure|surgery)\b", name):
        return "procedure/operative"
    if re.search(r"follow[ -]?up|progress|office|chart", name):
        return "follow-up/progress"
    if re.search(r"consult", name) or re.search(r"(?:^|[,\n])\s*reason for consult\w*\s*:", text):
        return "consultation"
    if re.search(r"history (?:and|&) physical|\bh\s*&\s*p\b", name) or re.search(r"(?:^|[,\n])\s*history (?:and|&) physical\s*:", text):
        return "history and physical"
    if (re.search(r"echocardiogram|electroencephalogram|\beeg\b|\bct\b|\bmri\b|x-ray|ultrasound", name) or row.medical_specialty == "Radiology") and not re.search(r"\bcourse\s*:", text):
        return "diagnostic report"
    return "other narrative/sectioned"


def clean_candidates(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Filter minimal text, then cluster exact and near-duplicate transcriptions.

    Near duplicates: word-five-shingle Jaccard >= .85 and normalized-token
    length ratio >= .8. Connected components prevent chain-linked duplicates
    from entering the subset together. Rare specialty labels win ties so that
    multi-listed reports do not all inherit the largest specialty's label.
    """
    working = frame.copy()
    working.insert(0, "source_row_id", np.arange(len(frame)))
    working["source_dataset_id"] = frame["Unnamed: 0"] if "Unnamed: 0" in frame else frame.index
    working.medical_specialty = working.medical_specialty.str.strip()
    working["word_count"] = word_counts(frame)
    audit = pd.DataFrame({"source_row_id": working.source_row_id, "exclusion_reason": "", "retained_source_row_id": working.source_row_id})
    for i, row in working.iterrows():
        text = row.transcription
        tokens = re.findall(r"[A-Za-z]+", text)
        if not text.strip():
            reason = "missing transcription"
        elif row.word_count < MIN_WORDS:
            reason = "fewer than 40 whitespace words (too little text for this subset)"
        elif len(set(t.lower() for t in tokens)) < 15:
            reason = "fewer than 15 distinct alphabetic tokens"
        elif sum(c.isalpha() for c in text) / max(sum(not c.isspace() for c in text), 1) < .5 or "\ufffd" in text or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            reason = "unreadable/control-character text"
        elif re.search(r":\s*[,;\s]*$", text):
            reason = "ends with an empty heading/field (apparent truncation)"
        elif re.search(r"\b(?:with|and|the|of|to|a|an|or|for|in|on|as|by|at)\s*[,\s]*$", text, re.I):
            reason = "ends mid-phrase (apparent truncation)"
        elif re.search(r"\btemplate\b|\bopening\s*$", row.sample_name, re.I):
            reason = "explicit template or standalone opening fragment"
        else:
            reason = ""
        audit.at[i, "exclusion_reason"] = reason
    usable = working.loc[audit.exclusion_reason.eq("")].copy()
    usable["_normalized"] = usable.transcription.map(normalize_text)
    specialty_counts = usable.medical_specialty.value_counts()
    def representative_key(row_id: int) -> tuple:
        specialty = working.at[row_id, "medical_specialty"]
        return (specialty not in SPECIALTY_TARGETS, int(specialty_counts[specialty]), row_id)
    groups = list(usable.groupby("_normalized", sort=True).groups.values())
    exact_reps = [min(group, key=representative_key) for group in groups]
    exact = usable.loc[exact_reps].sort_values("source_row_id")
    normalized = exact._normalized.tolist()
    matrix = CountVectorizer(ngram_range=(5, 5), binary=True, token_pattern=r"(?u)\b\w+\b", dtype=np.int32).fit_transform(normalized)
    sizes = np.asarray(matrix.sum(axis=1)).ravel()
    token_lengths = np.array([len(t.split()) for t in normalized])
    parent = list(range(len(exact)))
    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    pairs = []
    # Process sparse overlaps in blocks to avoid a dense NxN allocation.
    for start in range(0, len(exact), 128):
        overlaps = (matrix[start:start + 128] @ matrix.T).tocoo()
        for local_i, j, overlap in zip(overlaps.row, overlaps.col, overlaps.data):
            i = start + int(local_i)
            j = int(j)
            if i >= j or min(token_lengths[i], token_lengths[j]) / max(token_lengths[i], token_lengths[j]) < .8:
                continue
            similarity = float(overlap / (sizes[i] + sizes[j] - overlap))
            if similarity >= NEAR_DUPLICATE_JACCARD:
                parent[find(j)] = find(i)
                pairs.append((int(exact.index[i]), int(exact.index[j]), similarity))
    components = {}
    for i, row_id in enumerate(exact.index):
        components.setdefault(find(i), []).append(int(row_id))
    near_mapping = {}
    for members in components.values():
        chosen = min(members, key=representative_key)
        near_mapping.update({member: chosen for member in members})
    retained = []
    for group, exact_rep in zip(groups, exact_reps):
        final_rep = near_mapping[exact_rep]
        for row_id in group:
            audit.at[row_id, "retained_source_row_id"] = final_rep
            if row_id != exact_rep:
                audit.at[row_id, "exclusion_reason"] = "normalized duplicate transcription"
            elif row_id != final_rep:
                audit.at[row_id, "exclusion_reason"] = "near-duplicate transcription"
            else:
                retained.append(row_id)
    candidates = working.loc[sorted(retained)].copy()
    q1, q2 = candidates.word_count.quantile([1 / 3, 2 / 3])
    candidates["length_category"] = pd.cut(candidates.word_count, [-np.inf, q1, q2, np.inf], labels=list(LENGTH_TARGETS)).astype(str)
    candidates["content_indicators"] = candidates.transcription.map(lambda t: "; ".join(content_indicators(t)))
    candidates["structure_indicator"] = candidates.apply(structure_indicator, axis=1)
    lexical = candidates.transcription.map(lambda t: len({w.casefold() for w in re.findall(r"[A-Za-z]{9,}", t)}))
    numeric = candidates.transcription.map(lambda t: len(re.findall(r"\b\d+(?:\.\d+)?\b", t)))
    sections = candidates.transcription.map(lambda t: len(re.findall(r"(?:^|[,\n])\s*[A-Z][A-Z /&()-]{2,60}:", t)))
    cues = candidates.transcription.map(lambda t: len(content_indicators(t)))
    candidates["text_complexity_score"] = (lexical.rank(pct=True) + numeric.rank(pct=True) + sections.rank(pct=True) + cues.rank(pct=True)) / 4
    c1, c2 = candidates.text_complexity_score.quantile([1 / 3, 2 / 3])
    candidates["text_complexity_category"] = pd.cut(candidates.text_complexity_score, [-np.inf, c1, c2, np.inf], labels=["lower", "middle", "higher"]).astype(str)
    details = {
        "length_tertiles": [float(q1), float(q2)],
        "complexity_tertiles": [float(c1), float(c2)],
        "near_duplicate_pairs": pairs,
        "normalized_unique_before_near_dedup": len(exact),
        "candidate_count": len(candidates),
        "exclusions": audit.loc[audit.exclusion_reason.ne(""), "exclusion_reason"].value_counts().to_dict(),
    }
    return candidates, audit, details


def allocate_lengths(candidates: pd.DataFrame) -> dict[str, tuple[int, int, int]]:
    """Find a balanced integer allocation meeting specialty and length quotas."""
    counts = pd.crosstab(candidates.medical_specialty, candidates.length_category).reindex(index=list(SPECIALTY_TARGETS), columns=list(LENGTH_TARGETS), fill_value=0)
    order = sorted(SPECIALTY_TARGETS, key=lambda s: (int(counts.loc[s].sum()), s))
    options = {}
    for specialty in order:
        n = SPECIALTY_TARGETS[specialty]
        capacity = counts.loc[specialty].tolist()
        options[specialty] = sorted(
            [(a, b, n - a - b) for a in range(n + 1) for b in range(n - a + 1)
             if all(0 <= v <= cap and (cap == 0 or v >= 1) for v, cap in zip((a, b, n - a - b), capacity))],
            key=lambda x: (sum(v * v for v in x), x),
        )
    @lru_cache(None)
    def solve(i: int, remaining: tuple[int, int, int]):
        if i == len(order):
            return () if remaining == (0, 0, 0) else None
        for option in options[order[i]]:
            next_remaining = tuple(a - b for a, b in zip(remaining, option))
            if min(next_remaining) < 0:
                continue
            tail = solve(i + 1, next_remaining)
            if tail is not None:
                return (option,) + tail
        return None
    allocation = solve(0, tuple(LENGTH_TARGETS.values()))
    if allocation is None:
        raise ValueError("Source cannot satisfy the documented specialty/length quotas; review the sampling plan.")
    return dict(zip(order, allocation))


def select_reports(candidates: pd.DataFrame) -> pd.DataFrame:
    allocation = allocate_lengths(candidates)
    rng = np.random.default_rng(RANDOM_SEED)
    tie_break = dict(zip(candidates.index, rng.random(len(candidates))))
    slots = [(s, length, n) for s, values in allocation.items() for length, n in zip(LENGTH_TARGETS, values) if n]
    # Scarce cells first; choices within a cell maximize still-missing diversity.
    slots.sort(key=lambda slot: (int(((candidates.medical_specialty == slot[0]) & (candidates.length_category == slot[1])).sum()) / slot[2], slot[0], slot[1]))
    selected = []
    content_counts, structure_counts, complexity_counts = Counter(), Counter(), Counter()
    for specialty, length, n in slots:
        pool = candidates.loc[(candidates.medical_specialty == specialty) & (candidates.length_category == length)]
        for _ in range(n):
            def score(row_id):
                row = candidates.loc[row_id]
                cues = [cue for cue in row.content_indicators.split("; ") if cue]
                return (4 / (1 + complexity_counts[row.text_complexity_category])
                        + 3 / (1 + structure_counts[row.structure_indicator])
                        + sum(1 / (1 + content_counts[cue]) for cue in cues), tie_break[row_id])
            chosen = max((i for i in pool.index if i not in selected), key=score)
            selected.append(chosen)
            row = candidates.loc[chosen]
            content_counts.update(cue for cue in row.content_indicators.split("; ") if cue)
            structure_counts.update([row.structure_indicator])
            complexity_counts.update([row.text_complexity_category])
    result = candidates.loc[selected].sort_values(["medical_specialty", "word_count", "source_row_id"]).copy()
    result["selection_reason"] = result.apply(lambda r: f"{r.medical_specialty}; {r.length_category}; {r.structure_indicator}" + ("; " + " + ".join(r.content_indicators.split("; ")[:3]) if r.content_indicators else ""), axis=1)
    columns = ["source_row_id", *SOURCE_FIELDS, "word_count", "length_category", "selection_reason", "source_dataset_id", "structure_indicator", "text_complexity_category", "text_complexity_score", "content_indicators"]
    return result[columns].reset_index(drop=True)


def validate_selection(selected: pd.DataFrame, raw: pd.DataFrame, *,
                       specialty_targets=None, length_targets=None) -> None:
    specialty_targets = SPECIALTY_TARGETS if specialty_targets is None else specialty_targets
    length_targets = LENGTH_TARGETS if length_targets is None else length_targets
    assert len(selected) == 50 and selected.source_row_id.is_unique
    assert not blank_mask(selected.transcription).any()
    assert not selected.transcription.map(normalize_text).duplicated().any()
    assert selected.medical_specialty.value_counts().to_dict() == specialty_targets
    assert selected.length_category.value_counts().to_dict() == length_targets
    assert selected.medical_specialty.value_counts().max() <= 4
    assert set(selected.text_complexity_category) == {"lower", "middle", "higher"}
    assert selected.text_complexity_category.value_counts().min() >= 10
    assert selected.structure_indicator.nunique() >= 6
    counts = Counter(cue for text in selected.transcription for cue in content_indicators(text))
    assert set(counts) == set(CONTENT_PATTERNS) and min(counts.values()) >= 3
    shingles = []
    for row in selected.itertuples():
        assert row.transcription == raw.iloc[row.source_row_id].transcription
        assert row.word_count == len(row.transcription.split())
        tokens = normalize_text(row.transcription).split()
        shingles.append({tuple(tokens[i:i + 5]) for i in range(len(tokens) - 4)})
    # Stronger final check: no selected pair above the shingle threshold, even
    # without the cleaning stage's length-ratio gate.
    for i, a in enumerate(shingles):
        for b in shingles[i + 1:]:
            assert len(a & b) / len(a | b) < NEAR_DUPLICATE_JACCARD


def markdown_table(frame: pd.DataFrame) -> str:
    rows = [[str(c) for c in frame.columns]] + [[str(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in rows[0]) + " |"] + ["| " + " | ".join(row) + " |" for row in rows[1:]])


def distribution_table(series: pd.Series, name: str) -> str:
    return markdown_table(series.rename_axis(name).reset_index(name="Reports"))


def export_tables(selected: pd.DataFrame, audit: pd.DataFrame, outdir: Path) -> tuple[Path, Path]:
    """Write the single active CSV/Excel set and verify lossless round trips."""
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "mtsamples_curated_50.csv"
    excel_path = outdir / "mtsamples_curated_50.xlsx"
    selected.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        selected.to_excel(writer, index=False, sheet_name="Selected reports")
        sheet = writer.sheets["Selected reports"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        widths = {"transcription": 100, "selection_reason": 65, "description": 55, "keywords": 45, "content_indicators": 60, "sample_name": 40, "medical_specialty": 32}
        for column in sheet.columns:
            heading = column[0]
            sheet.column_dimensions[heading.column_letter].width = widths.get(heading.value, 24)
            heading.font = Font(bold=True, color="FFFFFF")
            heading.fill = PatternFill("solid", fgColor="244B5A")
            for cell in column:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if isinstance(cell.value, str):
                    cell.data_type = "s"
        sheet.row_dimensions[1].height = 32
        for row_num in range(2, len(selected) + 2):
            sheet.row_dimensions[row_num].height = 110
    # Full text round-trip checks catch Excel truncation and accidental changes.
    csv_back = pd.read_csv(csv_path, keep_default_na=False)
    excel_back = pd.read_excel(excel_path, keep_default_na=False)
    pd.testing.assert_frame_equal(csv_back, selected, check_dtype=False)
    pd.testing.assert_frame_equal(excel_back, selected, check_dtype=False)
    audit.to_csv(outdir / "candidate_audit.csv", index=False, lineterminator="\n")
    return csv_path, excel_path


def save_outputs(source: Path, raw: pd.DataFrame, candidates: pd.DataFrame, audit: pd.DataFrame, details: dict, selected: pd.DataFrame, outdir: Path) -> None:
    import sklearn
    import openpyxl
    validate_selection(selected, raw)
    csv_path, excel_path = export_tables(selected, audit, outdir)
    manifest = {
        "subset_version": "v1-proposed", "status": "selected source reports; awaiting team review and freeze; unannotated",
        "source_filename": source.name, "source_sha256": sha256(source), "source_rows": len(raw),
        "source_row_id_definition": "zero-based data-row position, excluding the header; source_dataset_id preserves Unnamed: 0 if present",
        "random_seed": RANDOM_SEED, "minimum_words": MIN_WORDS, "near_duplicate_jaccard": NEAR_DUPLICATE_JACCARD,
        "specialty_targets": SPECIALTY_TARGETS, "length_targets": LENGTH_TARGETS,
        "selected_source_row_ids": [int(i) for i in selected.source_row_id],
        "cleaning": details, "sampler_sha256": sha256(Path(__file__)),
        "versions": {"pandas": pd.__version__, "numpy": np.__version__, "scikit-learn": sklearn.__version__, "openpyxl": openpyxl.__version__},
        "output_sha256": {p.name: sha256(p) for p in [csv_path, excel_path, outdir / "candidate_audit.csv"]},
    }
    (outdir / "selection_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    eda = source_eda(raw)
    missing = eda["missing"].copy()
    missing.missing_percent = missing.missing_percent.map(lambda v: f"{v:.2f}%")
    q1, q2 = details["length_tertiles"]
    content_counts = Counter(cue for text in selected.transcription for cue in content_indicators(text))
    report = f"""# MTSamples: selected 50-report source evaluation subset

MTSamples is a collection of medical transcription sample reports. Each selected row's `transcription` is the source document for FaithfulMed's future simplification evaluation. This is a **selected evaluation subset**, not a cleaned replacement for the full dataset and not a claim of clinical correctness.

Status: **v1-proposed; selected, unannotated source reports awaiting team review and freeze**. These 50 reports are intended to become the team's shared/frozen baseline/evaluation set. No model outputs, clinical annotations, or gold simplified answers have been generated. Review and version this same set before reporting headline metrics. MedAESQA remains the separate Verifier calibration dataset.

## Source and sampling EDA

- Source file: `data/{source.name}`; {len(raw):,} rows and {len(raw.columns)} columns.
- Columns: {', '.join('`' + c + '`' for c in raw.columns)}.
- SHA-256: `{sha256(source)}`.
- Source identifiers: `source_row_id` is the zero-based data-row position excluding the header. `source_dataset_id` preserves the CSV's `Unnamed: 0` identifier (or the source row position if absent).
- {len(eda['specialties'])} original specialty labels; counts below include repeated reports under different labels.
- Exact duplicate full rows: {eda['duplicate_full_rows']}; duplicate rows excluding the index: {eda['duplicate_rows_without_index']}.
- Repeated nonempty transcription rows beyond the first: {eda['duplicate_transcriptions']:,} exact; {eda['duplicate_normalized_transcriptions']:,} after case/punctuation/whitespace normalization. Missing notes are excluded from duplicate counts.

{markdown_table(missing.rename_axis('Column').reset_index())}

Word counts use whitespace splitting. Statistics below exclude blank transcriptions; blank rows have zero words in the EDA.

{markdown_table(eda['word_stats'].round(2).rename_axis('Statistic').reset_index(name='Words'))}

{distribution_table(eda['specialties'], 'Original specialty')}

## Cleaning the candidate pool

The original file and original transcription strings were not modified. Filtering and normalization occur in memory only. Exclusions are sequential and mutually exclusive:

{distribution_table(pd.Series(details['exclusions']), 'Exclusion reason')}

The 40-word minimum excludes heading-only stubs and very short fragments observed during inspection. It is a conservative suitability rule for this subset, not a judgment that all shorter reports lack clinical value. Additional checks require 15 distinct alphabetic tokens, at least 50% alphabetic non-whitespace characters, no replacement/control characters, and no trailing empty heading/field (a final colon, optionally followed by commas/semicolons/whitespace). Reports ending mid-phrase with `with/and/the/of/to/a/an/or/for/in/on/as/by/at` are excluded, as are titles explicitly containing `template` or ending in `opening`. These rules were informed by inspected truncated and template records; they are conservative text-quality heuristics, not exhaustive judgments of completeness. No missing metadata is invented; missing description or keywords alone does not exclude a meaningful note. Absence of a regex content cue does not exclude a report: some meaningful diagnostic findings use different vocabulary. Heading-only/metadata fragments observed in the shortest rows fail the minimum-text checks.

Duplicate normalization case-folds and extracts word tokens. For each normalized duplicate group, prefer a label among the 15 target specialties, then the least frequent specialty in the usable pre-deduplication pool, then the lowest source row ID. This preserves actual source labels and avoids letting multi-listed notes all inherit a broad specialty. Near duplicates use sets of consecutive five-word shingles: Jaccard overlap >= {NEAR_DUPLICATE_JACCARD} with token-length ratio >= 0.8. Connected components are collapsed using the same representative rule; {len(details['near_duplicate_pairs'])} qualifying pairs were found. This conservative screen may remove minor clinical variants and cannot detect every semantic duplicate.

Remaining candidate pool: **{len(candidates):,} reports**. `candidate_audit.csv` records every source row's exclusion reason and final representative ID. An empty exclusion reason means retained in the candidate pool, not necessarily selected in the final 50. Representative IDs on quality-excluded rows are self-references only.

## Selection method

This is a purposive diversity set, not a prevalence-weighted population sample. Fifteen actual source specialty labels cover general care, organ systems, acute care, surgery, and different report formats. General Medicine, Cardiovascular / Pulmonary, Neurology, Emergency Room Reports, and Discharge Summary receive 4 reports each; the other 10 receive 3. Thus no specialty exceeds 8% of the subset. Source labels include both clinical disciplines and report types, so they are not a formal specialty ontology.

1. Compute length tertiles on the complete cleaned, deduplicated candidate pool: short <= **{q1:g}** words; medium > **{q1:g}** and <= **{q2:g}**; long > **{q2:g}**. Global quotas are 17 short, 17 medium, and 16 long.
2. Solve deterministic integer specialty/length quotas, requiring at least one of each available length group per specialty. Process specialties with fewer candidates first; choose the most even feasible allocation, with lexicographic tie-breaking.
3. Process specialty/length cells in ascending candidates-per-required-slot order, then specialty and length label. Greedily choose each report to increase diversity: score = 4/(1 + selected count in its complexity group) + 3/(1 + selected count of its structure) + sum of 1/(1 + selected count of each content cue). Break exact score ties using NumPy's seeded random ranks, assigned in ascending source-row order. **RANDOM_SEED = {RANDOM_SEED}**.
4. Complexity is a textual proxy: average candidate-pool percentile ranks of distinct alphabetic words of at least 9 letters, numeric-token count, uppercase section-heading count, and number of distinct content cues. Split that score into candidate-pool tertiles (lower/middle/higher). It is not medical severity or a clinical diagnosis. Structure uses a documented ordered set of title/heading checks in the sampler. Content indicators are case-insensitive regex presence cues in transcription text; they can match negated statements and are not verified clinical facts or gold annotations.
5. Preserve original text and source IDs; sort output by specialty, word count, and source row ID. Short reasons describe sampling features only. Validate size, provenance, exact/near-duplicate absence, quotas, at least 10 reports in each complexity group, at least 6 structures, and at least 3 reports matching every content cue. All 1,225 selected pairs are independently checked against the shingle threshold without the length-ratio gate.

## Final subset

{distribution_table(selected.medical_specialty.value_counts().sort_index(), 'Selected specialty')}

{distribution_table(selected.length_category.value_counts().reindex(list(LENGTH_TARGETS)), 'Length group')}

- Selected: **50**; mean words: **{selected.word_count.mean():.2f}**; median: **{selected.word_count.median():g}**.
- Shortest: **{selected.word_count.min()}** words (source row {int(selected.loc[selected.word_count.idxmin(), 'source_row_id'])}); longest: **{selected.word_count.max()}** words (source row {int(selected.loc[selected.word_count.idxmax(), 'source_row_id'])}).

{distribution_table(selected.structure_indicator.value_counts(), 'Structure indicator')}

{distribution_table(selected.text_complexity_category.value_counts().reindex(['lower', 'middle', 'higher']), 'Text complexity')}

Content counts overlap because one note can match multiple cues:

{distribution_table(pd.Series(content_counts).sort_index(), 'Content cue')}

## Reproduce and review

From the repository root, with dependencies in `requirements.txt` installed:

```powershell
python EDAs/mtsamples_sampling.py --profile mixed --source data/mtsamples.csv --output data/mtsamples_mixed_history
# Existing Windows virtual environment:
.\\.venv\\Scripts\\python.exe EDAs/mtsamples_sampling.py --profile mixed --source data/mtsamples.csv --output data/mtsamples_mixed_history
```

The sampler also accepts `.xlsx`/`.xlsm` input using pandas/openpyxl. It fails explicitly if another source cannot meet these quotas. For this version, verify the source hash above and use the library versions recorded in `selection_manifest.json`. Running the command overwrites generated subset artifacts; archive a reviewed/frozen version before deliberately changing source data or selection rules. CSV content, selected IDs, and metadata are deterministic; Excel archive timestamps may differ between runs.

This is the historical mixed-length profile. Open `EDAs/mtsamples_eda.ipynb` for both the historical and active medium-length analyses. The notebook does not overwrite exports. The reusable cleaning/selection implementation is `EDAs/mtsamples_sampling.py`. Its SHA-256 and selected row IDs are in the manifest.

Files: `mtsamples_curated_50.xlsx` (formatted sheet; expand row height/formula bar to read long notes), matching `mtsamples_curated_50.csv`, this README, `candidate_audit.csv`, and `selection_manifest.json`. The script verifies full CSV and Excel round-trips, including every transcription. Current repository rules ignore `data/curated_baseline/`; these local artifacts are not automatically tracked or published by Git.

Limitations: quota balancing intentionally changes specialty frequencies; only 15 of the 40 source labels are represented. Regex cues and text complexity are approximate sampling aids. This automated, reproducible selection is a proposal for team curation, not completed human annotation or clinical validation. Before freezing, the team should review whole reports for source suitability, structural classifications, residual duplicates, and intended coverage. No model generation or annotation is part of this task.
"""
    (outdir / "README.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/mtsamples.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/curated_baseline")
    parser.add_argument("--profile", choices=["medium", "mixed"], default="medium",
                        help="Medium is the active set; mixed reproduces the historical analysis.")
    args = parser.parse_args()
    if args.profile == "medium":
        try:
            from .mtsamples_medium_sampling import generate
        except ImportError:
            from mtsamples_medium_sampling import generate
        generate(args.source, args.output)
        return
    if args.output.resolve() == (ROOT / "data/curated_baseline").resolve():
        parser.error("Use --output with a different directory for historical mixed-length exports.")
    source_hash = sha256(args.source)
    raw = load_source(args.source)
    candidates, audit, details = clean_candidates(raw)
    selected = select_reports(candidates)
    validate_selection(selected, raw)
    # Recompute the seeded selection independently from the unchanged pool.
    pd.testing.assert_frame_equal(selected, select_reports(candidates))
    save_outputs(args.source, raw, candidates, audit, details, selected, args.output)
    assert sha256(args.source) == source_hash, "Source file changed during sampling."
    print(json.dumps({"original_rows": len(raw), "candidates": len(candidates), "exclusions": details["exclusions"], "length_tertiles": details["length_tertiles"]}, indent=2))
    print("\nSpecialties:\n", selected.medical_specialty.value_counts().sort_index().to_string())
    print("\nLengths:\n", selected.length_category.value_counts().to_string())
    print("\nWord counts:\n", selected.word_count.describe().to_string())
    print("\nStructures:\n", selected.structure_indicator.value_counts().to_string())
    print("\nComplexity:\n", selected.text_complexity_category.value_counts().to_string())
    print(f"\nValidated and saved to {args.output}")


if __name__ == "__main__":
    main()
