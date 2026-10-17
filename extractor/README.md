# Extractor handoff

Vaibhavi's [original progress notes](vaibhaviContext.md) document her earlier
MedlinePlus vector-store prototype. They are kept as a historical record. The
MiniLM code and local results were retired after the complete Gemini index
became the active retrieval source.

The [current Extractor handoff](EXTRACTOR_HANDOFF.md) summarizes the Gemini
retrieval path and Vaibhavi's ADK clinical-fact Extractor, including its smoke
tests and remaining integration step. The agent code is in
[`faithfulmed_demo/roles/extractor.py`](../faithfulmed_demo/roles/extractor.py).
For the shared Gemini index download and setup steps, see the
[MedlinePlus Gemini handoff](../data_pipeline/GEMINI_MEDLINEPLUS.md).
