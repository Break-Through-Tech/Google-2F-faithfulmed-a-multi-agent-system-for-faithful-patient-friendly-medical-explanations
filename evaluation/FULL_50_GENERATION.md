# 50-report Gemini comparison v1

Both systems attempted all 50 frozen MTSamples reports on November 23, 2026. This is the first completed 50-report generation comparison for Issue #32. The batch resumed from its checkpoint after an HTTP 402 interruption, preserving each recorded outcome.

| Generation outcome | Baseline | Full ADK |
| --- | ---: | ---: |
| Final answers | 45/50 (90%) | 34/50 (68%) |
| Drafts held for review | 0 | 4 |
| Failed attempts | 5 | 12 |
| Attempts with complete generation token totals | 50/50 | 44/50 |

Retrieved passages matched on 39 reports. The other 11 lacked comparable retrieval records. Among the 39 matches, both systems returned a final answer on 32 reports. Across those 32 pairs, the baseline averaged **4,707** Gemini generation tokens per report and ADK averaged **29,071**. These totals exclude retrieval embeddings.

The run used Gemini 3.8 Flash for both systems, the full source report as the retrieval query, and the top three passages from the frozen MedlinePlus index (`faithfulmed_medlineplus_gemini_embedding_2_768_v1`, embeddings from `gemini-embedding-2`). The baseline prompt fingerprint was `medlineplus-baseline-v3+01447b584f58`. ADK used the updated medication and readability prompts, fingerprinted as `adk-stages+6250f4e79957`.

The [fixed report list](frozen/full_50_report_ids_v1.json) records the frozen dataset version and report order. Its internal execution ID retains the `v2` suffix used by the runner when saving the checkpoints. The earlier deliberately stopped batch contributed no results to this comparison.
