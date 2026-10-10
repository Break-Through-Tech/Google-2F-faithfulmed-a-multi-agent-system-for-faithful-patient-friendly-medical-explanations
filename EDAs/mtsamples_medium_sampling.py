"""Active medium-length subset; preserve the original mixed-length sampler."""
from collections import Counter
from pathlib import Path
import json

import numpy as np
import pandas as pd

try:
    from . import mtsamples_sampling as base
except ImportError:
    import mtsamples_sampling as base

VERSION = "v3-medium-with-allergy-exceptions-proposed"
GAP_PATTERN = r"_{2,}|\[(?:inaudible|unintelligible)\]"
ALLERGY_EXCEPTION_IDS = (0, 4998)  # Allergic Rhinitis (204); Allergy Evaluation Consult (638).


def medium_pool(candidates):
    """Avoid explicit transcription blanks without rewriting or filling the source."""
    return candidates.loc[candidates.length_category.eq("medium")
                          & ~candidates.transcription.str.contains(GAP_PATTERN, case=False, regex=True)].copy()


def medium_targets(candidates):
    """Use the original specialty quotas, allowing two documented Allergy exceptions."""
    pool = selection_pool(candidates)
    capacity = pool.medical_specialty.value_counts()
    insufficient = {s: (n, int(capacity.get(s, 0))) for s, n in base.SPECIALTY_TARGETS.items()
                    if capacity.get(s, 0) < n}
    if insufficient:
        raise ValueError(f"Not enough eligible reports for original quotas: {insufficient}")
    return base.SPECIALTY_TARGETS.copy()


def selection_pool(candidates):
    """All screened medium reports plus two fixed, gap-free source exceptions."""
    exceptions = candidates.loc[candidates.source_row_id.isin(ALLERGY_EXCEPTION_IDS)].copy()
    if set(exceptions.source_row_id) != set(ALLERGY_EXCEPTION_IDS):
        raise ValueError("Documented Allergy exception source IDs are missing after cleaning.")
    if (not exceptions.medical_specialty.eq("Allergy / Immunology").all()
            or exceptions.length_category.eq("medium").any()
            or exceptions.transcription.str.contains(GAP_PATTERN, case=False, regex=True).any()):
        raise ValueError("Documented Allergy exceptions no longer meet the selection rules.")
    expected = {0: ("Allergic Rhinitis", 204), 4998: ("Allergy Evaluation Consult", 638)}
    observed = {int(r.source_row_id): (r.sample_name.strip(), int(r.word_count))
                for r in exceptions.itertuples()}
    if observed != expected:
        raise ValueError("Documented Allergy exceptions no longer match their source reports.")
    return pd.concat([medium_pool(candidates), exceptions]).sort_values("source_row_id")


def select_medium_reports(candidates):
    """Greedy diversity selection with two fixed Allergy length exceptions."""
    pool = selection_pool(candidates)
    targets = medium_targets(candidates)
    capacity = pool.medical_specialty.value_counts()
    order = sorted(targets, key=lambda s: (int(capacity[s]) / targets[s], s))
    rng = np.random.default_rng(base.RANDOM_SEED)
    ties = dict(zip(pool.index, rng.random(len(pool))))
    chosen = []
    content, structures, complexities = Counter(), Counter(), Counter()
    for specialty in order:
        eligible = pool.loc[pool.medical_specialty.eq(specialty)]
        for _ in range(targets[specialty]):
            def score(i):
                row = pool.loc[i]
                cues = [cue for cue in row.content_indicators.split("; ") if cue]
                return (4 / (1 + complexities[row.text_complexity_category])
                        + 3 / (1 + structures[row.structure_indicator])
                        + sum(1 / (1 + content[cue]) for cue in cues), ties[i])
            ident = max((i for i in eligible.index if i not in chosen), key=score)
            chosen.append(ident)
            row = pool.loc[ident]
            content.update(c for c in row.content_indicators.split("; ") if c)
            structures.update([row.structure_indicator])
            complexities.update([row.text_complexity_category])
    selected = pool.loc[chosen].sort_values(["medical_specialty", "word_count", "source_row_id"]).copy()
    selected["selection_reason"] = selected.apply(
        lambda r: f"{r.medical_specialty}; {r.length_category}"
        + (" (documented Allergy length exception)" if r.source_row_id in ALLERGY_EXCEPTION_IDS else "")
        + f"; {r.structure_indicator}; {r.text_complexity_category} text complexity"
        + ("; " + " + ".join(r.content_indicators.split("; ")[:3]) if r.content_indicators else ""), axis=1)
    columns = ["source_row_id", *base.SOURCE_FIELDS, "word_count", "length_category", "selection_reason",
               "source_dataset_id", "structure_indicator", "text_complexity_category", "text_complexity_score", "content_indicators"]
    return selected[columns].reset_index(drop=True)


def validate_medium_selection(selected, raw, candidates):
    base.validate_selection(selected, raw, specialty_targets=medium_targets(candidates),
                            length_targets={"medium": 48, "short": 1, "long": 1})
    q1, q2 = candidates.word_count.quantile([1 / 3, 2 / 3])
    assert set(selected.loc[selected.length_category.ne("medium"), "source_row_id"]) == set(ALLERGY_EXCEPTION_IDS)
    medium_selected = selected.loc[selected.length_category.eq("medium")]
    assert medium_selected.word_count.gt(q1).all() and medium_selected.word_count.le(q2).all()
    medium_ids = set(medium_pool(candidates).source_row_id)
    assert set(medium_selected.source_row_id) <= medium_ids


def selection_audit(audit, candidates, selected):
    """Separate quality exclusions, length eligibility, quotas, and final selection."""
    result = audit.copy()
    indexed = candidates.set_index("source_row_id")
    result["length_category"] = result.source_row_id.map(indexed.length_category).fillna("")
    result["selected"] = result.source_row_id.isin(selected.source_row_id)
    def status(row):
        if row.exclusion_reason:
            return "excluded during cleaning"
        if row.selected and row.source_row_id in ALLERGY_EXCEPTION_IDS:
            return "selected Allergy length exception"
        if row.length_category != "medium":
            return "cleaned report outside medium length range"
        if row.source_row_id not in screened_ids:
            return "medium report with explicit transcription gap"
        if indexed.at[row.source_row_id, "medical_specialty"] not in base.SPECIALTY_TARGETS:
            return "medium report outside target specialties"
        return "selected" if row.selected else "eligible medium report not selected"
    screened_ids = set(medium_pool(candidates).source_row_id)
    result["selection_status"] = result.apply(status, axis=1)
    return result


def save_medium_outputs(source, raw, candidates, audit, details, selected, outdir):
    import sklearn
    import openpyxl
    validate_medium_selection(selected, raw, candidates)
    csv_path, excel_path = base.export_tables(selected, selection_audit(audit, candidates, selected), outdir)
    medium = candidates.loc[candidates.length_category.eq("medium")]
    screened = medium_pool(candidates)
    q1, q2 = details["length_tertiles"]
    manifest = {
        "subset_version": VERSION, "sampling_profile": "medium", "supersedes": "v1-proposed (mixed lengths)",
        "status": "selected source reports; awaiting team review and freeze; unannotated",
        "source_filename": source.name, "source_sha256": base.sha256(source), "source_rows": len(raw),
        "source_row_id_definition": "zero-based data-row position, excluding the header; source_dataset_id preserves Unnamed: 0 if present",
        "random_seed": base.RANDOM_SEED, "minimum_words": base.MIN_WORDS,
        "near_duplicate_jaccard": base.NEAR_DUPLICATE_JACCARD,
        "specialty_targets": medium_targets(candidates), "length_targets": {"medium": 48, "short": 1, "long": 1},
        "documented_length_exceptions": [
            {"source_row_id": int(r.source_row_id), "sample_name": r.sample_name.strip(),
             "word_count": int(r.word_count), "length_category": r.length_category,
             "reason": "Allergy/Immunology has only one medium-length source report; this complete, gap-free allergy report restores the original three-report quota"}
            for r in selected.itertuples() if r.source_row_id in ALLERGY_EXCEPTION_IDS],
        "medium_word_range": {"lower_exclusive": q1, "upper_inclusive": q2},
        "medium_candidate_count": len(medium),
        "medium_after_gap_screen": len(screened), "transcription_gap_pattern": GAP_PATTERN,
        "medium_target_specialty_candidate_count": int(screened.medical_specialty.isin(base.SPECIALTY_TARGETS).sum()),
        "selected_source_row_ids": [int(i) for i in selected.source_row_id],
        "cleaning": details,
        "sampler_sha256": {"mtsamples_sampling.py": base.sha256(Path(base.__file__)),
                           "mtsamples_medium_sampling.py": base.sha256(Path(__file__))},
        "versions": {"pandas": pd.__version__, "numpy": np.__version__, "scikit-learn": sklearn.__version__, "openpyxl": openpyxl.__version__},
        "output_sha256": {p.name: base.sha256(p) for p in [csv_path, excel_path, outdir / "candidate_audit.csv"]},
    }
    (outdir / "selection_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    counts = Counter(cue for text in selected.transcription for cue in base.content_indicators(text))
    targets = medium_targets(candidates)
    quota_table = pd.DataFrame({"specialty": list(base.SPECIALTY_TARGETS),
        "previous_target": list(base.SPECIALTY_TARGETS.values()),
        "medium_available_after_gap_screen": [int(screened.medical_specialty.eq(s).sum()) for s in base.SPECIALTY_TARGETS],
        "documented_length_exceptions": [2 if s == "Allergy / Immunology" else 0 for s in base.SPECIALTY_TARGETS],
        "selected_target": [targets.get(s, 0) for s in base.SPECIALTY_TARGETS]})
    report = f"""# MTSamples: active 50-report medium-focused subset

Status: **{VERSION}; awaiting team review and freeze**. This is the single active curated set, following Samaneh's recommendation to use medium-length reports for the first baseline. It replaces the mixed-length CSV and Excel at the same paths. The earlier analysis and selected IDs remain reproducible in `EDAs/mtsamples_eda.ipynb`; the original exports remain in Git history (commit `5d415c7`). No generated explanations or gold annotations are included.

## Source and cleaning

Source: `data/{source.name}`; **{len(raw):,} rows**; SHA-256 `{base.sha256(source)}`.
The unchanged cleaning rules remove empty/very short text, obvious truncation and template fragments, normalized duplicates, and near-duplicates. Near-duplicate detection uses five-word shingle Jaccard >= {base.NEAR_DUPLICATE_JACCARD} with length ratio >= 0.8. The original transcription text is preserved exactly.

{base.distribution_table(pd.Series(details['exclusions']), 'Cleaning exclusion')}

**{len(candidates):,} cleaned reports remain; {len(medium):,} are medium-length.** Medium means more than **{q1:g}** and at most **{q2:g} whitespace words**, using the middle third of the complete cleaned pool. These cutoffs are not recomputed within specialties or within the final 50. The active set has 48 medium reports and two documented Allergy/Immunology length exceptions.

## How these 50 were chosen

1. Start with the same quality-screened, deduplicated pool used for the original EDA, and keep medium reports. Exclude explicit transcription gaps (two or more underscores, or bracketed inaudible/unintelligible markers): {len(medium) - len(screened)} medium reports are excluded and {len(screened)} remain. This conservative extra screen avoids incomplete passages without filling in missing text; it can also exclude harmless redactions. The original mixed-length cleaning and analysis are unchanged.
2. Restore the original three-report Allergy/Immunology quota with two fixed, complete, gap-free source reports outside the medium range: **source row 0, Allergic Rhinitis (204 words, short)**, and **source row 4998, Allergy Evaluation Consult (638 words, long)**. They are direct allergy cases and add one shorter and one longer format to the 390-word medium asthma report. The other specialty quotas return to the original targets, including three each for Orthopedic and Surgery. All other 48 selected reports must be medium-length. This deliberate exception means the set is medium-focused, not strictly medium-only.
3. Process scarce specialties first (available reports divided by quota). Choose reports greedily to add less-represented content cues, report structures, and text-complexity groups. The diversity score is `4/(1+complexity_count) + 3/(1+structure_count) + sum(1/(1+content_cue_count))`. Seed {base.RANDOM_SEED} breaks ties with ranks assigned in source-row order.
4. Keep the original cleaned-pool complexity cutoffs so comparisons with the earlier sample are consistent. Text complexity and regex cues are sampling aids; they are not clinical labels and can match negated statements.
5. Validate 50 unique IDs, exact source-text preservation, the 48/1/1 length split and specialty quotas, at least 10 reports per complexity group, at least six structures, and at least three matches for every content cue. Check all 1,225 selected pairs for near-duplicates, without the length-ratio gate.

This is a reproducible diversity selection, not a claim of the clinically "best" 50. The quality filters cannot catch every incomplete or inaccurate source report; team review is still required. Selection does not use any generated output or evaluation score.

{base.markdown_table(quota_table)}

## Selected-set coverage

- **48 medium-length reports, one short Allergy exception, and one long Allergy exception**, spanning {selected.medical_specialty.nunique()} source labels (specialties and report formats).
- Word counts: minimum **{selected.word_count.min()}**, median **{selected.word_count.median():g}**, mean **{selected.word_count.mean():.2f}**, maximum **{selected.word_count.max()}**.

{base.distribution_table(selected.structure_indicator.value_counts(), 'Structure')}

{base.distribution_table(selected.text_complexity_category.value_counts().reindex(['lower', 'middle', 'higher']), 'Text complexity')}

Content cue counts overlap:

{base.distribution_table(pd.Series(counts).sort_index(), 'Content cue')}

## Files and reproduction

- `mtsamples_curated_50.csv` and `.xlsx`: the same active medium-focused set, in two convenient formats.
- `candidate_audit.csv`: each original row's cleaning decision and selection status. Eligible but unselected reports are distinguished from quality exclusions and out-of-range reports.
- `selection_manifest.json`: source and output hashes, selected IDs, cutoffs, quotas, code hashes, and library versions.

Run from the repository root:

```text
python EDAs/mtsamples_sampling.py --profile medium --source data/mtsamples.csv
```

The default profile is now `medium` (48 medium reports plus two documented length exceptions). The original mixed-length functions remain unchanged; to reproduce their exports separately use `--profile mixed --output <another-directory>`. The notebook displays both analyses but compares the active exports only with the new medium-focused set. CSV/Excel full-text round trips are checked. These existing output files are already tracked by Git; ignoring `data/` does not hide changes to them. Only one active export set is kept here.

Review complete reports before freezing this version. Results on this set mainly describe medium-length notes from these source categories, with two explicit Allergy exceptions; they do not establish general performance on short/long reports or clinical reliability.
"""
    (outdir / "README.md").write_text(report, encoding="utf-8")


def generate(source, outdir):
    source_hash = base.sha256(source)
    raw = base.load_source(source)
    candidates, audit, details = base.clean_candidates(raw)
    selected = select_medium_reports(candidates)
    validate_medium_selection(selected, raw, candidates)
    pd.testing.assert_frame_equal(selected, select_medium_reports(candidates))
    save_medium_outputs(source, raw, candidates, audit, details, selected, outdir)
    assert base.sha256(source) == source_hash, "Source changed during sampling."
    print(json.dumps({"version": VERSION, "cleaned_candidates": len(candidates),
        "medium_candidates": int(candidates.length_category.eq('medium').sum()),
        "selected": len(selected), "word_range": [int(selected.word_count.min()), int(selected.word_count.max())],
        "specialties": selected.medical_specialty.value_counts().to_dict(),
        "complexity": selected.text_complexity_category.value_counts().to_dict()}, indent=2))
