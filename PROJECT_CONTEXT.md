# FaithfulMed — Extractor Project Context

Last updated: 2026-10-03. Owner: Vaibhavi Srivastava. This describes generated and tested code in this task folder; it does not imply the owner has run it personally or pushed it yet.

## 1. Project Goal
FaithfulMed is a Google-hosted Break Through Tech AI Studio Fall 2026 project for patient-friendly explanations that remain faithful to clinical sources. The official architecture has Extractor, Simplifier, Verifier, Refiner, and Readability agents. September builds EDA, retrieval, a single-Gemini baseline, and evaluation. October adds Google ADK orchestration and clinical-atom extraction.

Source: [Challenge Project Overview](https://github.com/Break-Through-Tech/Google-2F-faithfulmed-a-multi-agent-system-for-faithful-patient-friendly-medical-explanations/blob/main/Challenge-Project-Overview.md), retrieved 2026-10-03, plus the user's September task assignment. Advisor's Oct 1 guidance supplied earlier in this conversation narrows RAG to MedlinePlus.

## 2. My Role / Task
Vaibhavi owns the September ChromaDB infrastructure: ingest the Simplifier owner's prepared embeddings, retain source metadata, implement top-three similarity search, document the interface, and inspect clinical inputs. The eventual Extractor agent will return typed clinical facts. The current retrieval component returns definitions and sources; it does not perform full free-text clinical extraction or generate patient advice.

## 3. September Milestone Responsibilities
- Deep-dive EDA on MTSamples and a Synthea sample; document structure and limitations.
- Set up persistent ChromaDB and ingestion of cleaned/embedded lay-language content.
- Define collection name, chunk metadata, and a framework-neutral retrieval interface.
- Test medical-term queries returning relevant lay-language definitions.
- Contribute to the shared approximately 50-example frozen baseline set (not completed here).
- Document work, assumptions, decisions, blockers, and next steps; coordinate major architecture choices with the team.

## 4. Datasets / Inputs Used
- `mtsamples.csv`: 4,999 transcribed-report rows; clinical input EDA, not the RAG corpus.
- Eight uploaded Synthea FHIR JSON Bundles: synthetic clinical input EDA and deterministic flattening.
- `RAG_Embeddings_Full (1).jsonl`: Ruhma's real handoff, 18,343 records; only its 1,015 MedlinePlus records are indexed. Its 16,407 MedQuAD and 921 PLABA records are excluded from this index.
- Updated `medical_rag_pipeline`: notebook JSON without an extension; its final embedding cell uses `all-MiniLM-L6-v2`. The earlier notebook and accompanying README described Gemini; prefer the updated code for this actual handoff.
- `medaesqa_v1.json`: 40 questions, expert nuggets, and 30 machine answers per question. Evaluation backbone, not indexed or trained on.
- Uploaded Verifier notebook/context/README and readability harness were reviewed for team boundaries. Their code was not merged into this folder. The uploaded `PROJECT_CONTEXT.md` belongs to the Verifier; this is a separate Extractor context file.

Raw datasets and embedding files stay outside the commit-ready folder.

## 5. Data Structure
MTSamples CSV: an unnamed identifier column (`""`), `description`, `medical_specialty`, `sample_name`, `transcription`, `keywords`.

Synthea: `resourceType=Bundle`, `entry[]`, nested `entry.resource` objects with `resourceType` and `id`. Medication references can use `Medication/id` or `urn:uuid`; URNs resolve against entry `fullUrl`.

Embedding JSONL: one object per line with `Medical_Term`, `Lay_Language_Definition`, `Text_to_Embed`, `Embedding`, and `Metadata` (`source`, `url` for MedlinePlus). There is also a misspelled `Lay_Language_Definiton` column used in the mixed handoff; the MedlinePlus path uses the correctly spelled field. Vectors are 384 numbers. Model identity is documented by the supplied notebook; vector dimension alone cannot prove identity.

Stored metadata: `source`, `source_id` (URL), `url`, `term`, plain-text `definition`, `chunk_index=0`. Documents preserve exact `Text_to_Embed` so they match the supplied vectors. SHA-256 IDs identify URL/term/embedded-text combinations. Search outputs: `id`, `text`, `definition`, `metadata`, `distance`; lower cosine distance is closer.

## 6. Work Completed So Far
- Earlier prototype scripts audited MTSamples, Synthea, and MedAESQA; deterministic FHIR flattening resolves medication references.
- `rag.py` now parses Ruhma's actual uppercase JSONL schema, filters to MedlinePlus, validates all selected records before writing, rejects malformed/missing/vector-invalid selected records, and deduplicates identical records.
- Real Chroma ingestion of all 1,015 MedlinePlus records succeeded on local `/tmp` storage; repeated ingestion remained 1,015. Reopened SQLite integrity check returned `ok`.
- Five stored-vector self-retrieval smoke checks passed. Real text searches ran for hypertension, diabetes, myocardial infarction, A1C, and asthma using the matching MiniLM model.
- Eight tests passed covering earlier utilities and new schema validation, source filtering, duplicate handling, persistence, idempotence, vector retrieval, and model-mismatch rejection.
- Added and tested a wrapper against Rafi's actual repository adapter: hypertension returned three records using matching MiniLM embeddings.
- Created the walkthrough notebook, README, validation report, and this context file. All four notebook code cells were executed sequentially in a Python process and outputs saved; notebook schema validated. A Jupyter-kernel run was blocked by this runtime's socket restrictions, so Colab execution remains a user check. Code is prepared for upload, not pushed.

## 7. Key Findings
- MTSamples: 33 missing transcriptions, 6 missing descriptions, 1,149 missing keyword values. Among 4,966 nonempty transcriptions, 2,357 distinct stripped texts; 2,609 repeated occurrences. No exact whole-row duplicates. Specialty values have leading whitespace; there are 40 normalized specialties. Avoid duplicate-text leakage in future evaluation splits.
- Synthea: eight Bundles contain 12,926 resources, dominated by 6,181 Observations. All resources have IDs. Flattening six selected resource types yields 9,554 resource-level records; these are not validated atomic clinical facts. All 315 MedicationRequests have names after inline or referenced resolution.
- The embedding file is nonempty. All 1,015 selected MedlinePlus records have required fields and finite nonzero 384-dimensional vectors; no duplicate IDs in the selected input.
- Hypertension retrieved high-blood-pressure topics. Myocardial infarction retrieved Heart Attack second, behind Cardiomyopathy. A1C retrieved A1C first but broad unrelated lower-ranked topics. These are smoke examples, not a frozen gold-set accuracy measure.
- The actual MiniLM model has a 256-token sequence limit. Long supplied topic summaries are truncated during embedding; full-document retrieval may lose later details.
- A workspace-backed Chroma database became malformed on reopening. Rebuilding on local `/tmp` storage passed persistence and integrity checks. Root cause is unconfirmed; recommend local disk for the active SQLite database, especially in Colab.

## 8. Technical Decisions
- Index MedlinePlus only; keep clinical inputs separate from supporting lay-language retrieval.
- Reuse supplied MiniLM document vectors and matching MiniLM query embeddings. This is a documented fallback/deviation from the overview's Gemini embedding milestone. Gemini migration needs a coordinated full re-embedding and a separate collection.
- Collection: `faithfulmed_medlineplus_minilm_v1`; cosine distance; collection metadata locks model, dimension, and schema version.
- Preserve original embedded text; strip HTML only in returned/display definitions. No new chunking during ingestion. Later chunking requires re-embedding.
- Stable IDs plus upsert support repeat ingestion. Changed content can leave obsolete IDs; use a fresh versioned collection for revised snapshots.
- Default top-k is 3. No relevance threshold is calibrated; every returned hit is not necessarily relevant. Preserve source attribution and inspect results downstream.
- Plain Python, no September multi-agent loop. `extractor.py` is the legacy prototype; `rag.py` is the current entry point.
- Active DB on local disk; exclude raw data, embeddings, database directories, and keys from GitHub uploads.

## 9. Current Files
| File | Purpose |
|---|---|
| `rag.py` | Current index ingestion, validation, retrieval, context formatting, Rafi-compatible wrapper |
| `Extractor_Vector_Store.ipynb` | Setup and reproducible walkthrough |
| `PROJECT_CONTEXT.md` | Extractor continuity notes and log |
| `VALIDATION.json` | Actual counts, persistence check, five-query retrieval observations, tested versions |
| `README.md`, `requirements.txt` | Run instructions, handoff contract, tested dependency versions |
| `MTSAMPLES_EDA.md`, `SYNTHEA_EDA.md` | Earlier sample EDA reports |
| `extractor.py` | Earlier audit/field extraction helpers and separate legacy ingestion prototype |
| `fhir.py`, `synthea_audit.py`, `medaesqa_audit.py` | Clinical-data flattening and structure audits |
| `tests/` | Eight tests at last full run |
| `examples/chunks.jsonl` | Fabricated legacy toy fixture; never ingest into current MiniLM collection |

## 10. Dependencies
Ruhma's real embedding handoff has arrived. The team still needs to agree whether to retain the MiniLM fallback or regenerate Gemini embeddings. Rafi's repository adapter calls `query_texts`; use `TextQueryCollection` from this folder to keep embedding models consistent. He and the Simplifier/Refiner owners need the DB path, collection name, embedding model, metadata contract, and retrieval results.

The baseline-generation pipeline and readability/faithfulness evaluation are other owners' tasks; no end-to-end baseline run occurred here. Current GitHub connection reports `push=false`, so upload must use the owner's account or separately granted write access. The user said they have not opened earlier generated code yet.

## 11. Next Steps
1. Open the walkthrough notebook and run it with the actual JSONL path on local disk/Colab.
2. Upload this code/docs folder under the owner's task directory using their GitHub account; do not upload the raw data or DB.
3. Connect Rafi's adapter and the Simplifier's pipeline to the real collection, then test an end-to-end baseline.
4. Review/label a frozen retrieval evaluation set; assess top-three relevance and calibrate a cutoff if appropriate.
5. Agree on embedding model, HTML preprocessing, chunk sizes, and a versioned re-embedding plan with Ruhma; consider the 256-token truncation.
6. Contribute baseline examples and record team decisions in ADRs. October: build and validate typed clinical-atom extraction with ADK.

## 12. Session Log
### Earlier work in this conversation (exact dates not recorded)
- Worked on: extractor prototype, MTSamples/Synthea/MedAESQA inspection, medication-reference flattening.
- Changed: generated audit/flattening scripts, toy tests, EDA docs, earlier ZIP versions.
- Findings: missing/duplicate MTSamples text; nested Synthea Bundles; medication URN references.
- Decisions: clinical-data understanding first; no complete free-text LLM extractor yet.
- Blockers: actual embedding handoff had not been checked.
- Next step: inspect Ruhma's real output and implement ingestion against its actual schema.

### 2026-10-03
- Worked on: supplied updated Simplifier notebook/JSONL; team handoff; actual Chroma infrastructure.
- Changed: added `rag.py`, retrieval wrapper, validation tests/report, walkthrough notebook, current README, pinned tested dependencies, and this context file.
- Findings: 18,343 rows, 1,015 MedlinePlus; actual MiniLM model differs from README; five term searches run; lower-ranked relevance is imperfect; local-disk persistence passed after workspace SQLite corruption.
- Decisions: MedlinePlus-only MiniLM collection; exact embedded documents with clean display text; no mixed-model search; local live DB; plain Python top-three interface.
- Blockers: read-only connected GitHub account; no frozen-set retrieval evaluation, Gemini re-embedding, or complete pipeline integration.
- Next step: user opens notebook and uploads code through their account, then team integrates retrieval.

Update this file after meaningful work. Preserve verified results and distinguish implemented code, smoke tests, and evaluated quality.
