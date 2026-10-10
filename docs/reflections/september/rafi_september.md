# September Reflection: Sajib "Rafi" Hossain

## Name

Sajib "Rafi" Hossain — Verifier Agent Owner

## Date / Week

September 1–30, 2026.

## What I Worked On

I explored MedAESQA to understand its nested questions, machine-generated answers, sentence relevance labels, and citation assessments. I analyzed the label distributions and extracted examples of supported, unreferenced, irrelevant, neutral, invalid-citation, and contradictory evidence.

I developed a deterministic rubric that classifies sentences using these existing annotations and assigns an answer the highest-risk category found in its sentences. I added tests and documented the rules as a foundation for the later Verifier implementation.

I also built a framework-neutral retrieval adapter that accepts a medical query, queries a Chroma-compatible collection, and returns text, metadata, IDs, and distances. I tested it with mock collections while waiting for the shared vector store.

For the shared baseline set, I created a sampling-focused MTSamples EDA and a reproducible selection of 50 reports. The work includes a sampling script, Excel and CSV outputs, an exclusion audit, and a manifest recording source IDs, hashes, and selection settings. I also contributed the shared documentation structure and guidance for ADRs and individual reflections.

## What I Learned

An answer can be labeled accurate overall while still containing weak or incorrect citations. This made sentence-level evidence assessment important to my Verifier design. Missing citations also do not automatically mean a statement is false.

I learned that unique dataset rows are not necessarily unique reports: MTSamples repeats many transcriptions under different specialty labels. Deduplication, traceable source IDs, and documented sampling rules are necessary for a useful evaluation set.

Testing the retrieval interface independently helped me make progress before the upstream data and ChromaDB integration were available.

## Results / Findings

- MedAESQA contains 40 questions, 1,200 machine-generated answers, 5,162 sentences, and 9,611 citation assessments. Although 91.83% of answers are labeled accurate, only 67.53% of citation assessments are supporting. These are dataset findings, not FaithfulMed performance results.
- The rubric and retrieval adapter had six and five passing unit tests, respectively, at the initial foundation stage.
- MTSamples has 4,999 rows across 40 specialty labels, including 33 missing transcriptions and 2,609 exact repeated nonempty transcriptions beyond the first occurrence.
- The original September subset contained 50 unchanged source reports across 15 specialty labels: 17 short, 17 medium, and 16 long. Selection used cleaned-pool length quantiles and seed 42. An early October revision now proposes 48 medium-length reports and two documented Allergy/Immunology exceptions for team review.

## Challenges / Blockers

Real retrieval integration still depends on the team's populated ChromaDB collection and an agreed metadata and embedding interface. Mock tests verify adapter behavior but do not establish retrieval quality on the actual index.

The rubric uses existing MedAESQA annotations; it does not yet independently evaluate new baseline explanations. Baseline faithfulness evaluation requires generated outputs and agreed review labels. The selected 50 reports also need team review and finalization before they become a frozen evaluation set.

## Decisions / Contributions

I kept retrieval compatible with plain Python and future Google ADK integration. I preserved MedAESQA's role as the Verifier calibration dataset and used MTSamples for the shared source-report subset. The sampling process preserves original transcription text and makes each selected report traceable to its source row.

As an early October follow-up to the September evaluation work, I helped extend Alicia's readability notebook. Her original metrics, starter vocabulary, and examples remain the foundation. I made the scoring reusable from a Python module, moved the notebook into `evaluation/`, replaced its Colab-only download step with local CSV output, improved sentence counting, added refusal detection, and connected it to the baseline output format. This was collaboration on Alicia's work, not a claim that I built her initial harness or that these changes were completed in September.

## Next Steps

- Review and freeze the proposed medium-focused 50-report subset with the team. This revision followed challenge advisor Samaneh's recommendation to focus on medium-length reports; two clearly documented Allergy/Immunology length exceptions preserve that specialty's original three-report target.
- Connect the retrieval adapter to the populated ChromaDB collection and validate representative queries once the upstream handoff is ready.
- Apply the rubric to baseline outputs and agree on how to record unsupported additions, omissions, and contradictions.
- Evaluate faithfulness alongside Alicia's readability metrics once the shared baseline outputs are available.
