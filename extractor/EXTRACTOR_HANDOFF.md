# Extractor handoff and current status

Vaibhavi's September prototype searched MedlinePlus records in a local ChromaDB
collection using MiniLM vectors. It established a retrieval interface and
demonstrated searches. That interim code, notebook, dependency pins, input
vectors, and generated results were retired after the complete Gemini index was
verified. The historical implementation remains in Git history.

Current MedlinePlus retrieval uses the [Gemini index](../data_pipeline/GEMINI_MEDLINEPLUS.md)
and [retrieval adapter](../retrieval/README.md). Its Chroma collection contains
6,883 chunks; document and query embeddings use `gemini-embedding-2`.

## October 16, 2026: ADK clinical fact Extractor

Vaibhavi added [`faithfulmed_demo/roles/extractor.py`](../faithfulmed_demo/roles/extractor.py)
and [`faithfulmed_demo/test_extractor.py`](../faithfulmed_demo/test_extractor.py).
The agent reads `source_report` and writes structured `atoms`. Each atom has
text, type, assertion status, and an exact source quote.

She ran a live Gemini 3.8 Flash smoke test on a synthetic chest-pain note and
observed preservation of pending results, uncertainty, follow-up times, and
conditional medications. Schema and source-quote checks passed. A synthetic
penicillin/metformin example passed automatic checks for negation and the
"500 mg twice daily" dose. The checked-in test covers that second example.
These are smoke tests, not a clinical accuracy benchmark.

The next step is integration into the shared ADK pipeline. Integration must
call `validate_source_quotes` explicitly; creating the agent does not
automatically enforce quote validation.
