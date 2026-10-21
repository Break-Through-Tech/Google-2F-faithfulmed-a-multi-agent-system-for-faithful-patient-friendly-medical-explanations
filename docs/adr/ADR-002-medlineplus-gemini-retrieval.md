# ADR-002: MedlinePlus-only Gemini retrieval index

## Status

Accepted by Rafi on 2026-10-20 for the current MedlinePlus retrieval design.

## Date

2026-10-20

## Decision owner

Rafi Hossain, retrieval and Verifier owner.

## Context

The baseline and future agents need plain-language medical passages they can trace to a source. Clinical reports are inputs to explain, while MedAESQA is used to study and evaluate faithfulness; neither should silently become the retrieval knowledge base. The team narrowed its initial RAG source to MedlinePlus. An earlier MiniLM index allowed retrieval work to proceed while Gemini embedding was limited by API quota. The complete Gemini index is now available.

## Decision

Use cleaned MedlinePlus topics as the sole source for the initial shared retrieval collection. Split definitions into chunks of at most 800 characters while preserving each topic's ID, title, URL, and chunk number. Embed all stored chunks and live search queries with `gemini-embedding-2` at 768 dimensions, and store the chunk text, metadata, and vectors in a versioned local ChromaDB collection using cosine distance. Do not mix vectors from different embedding models in one collection.

Expose retrieval through the framework-neutral `retrieve_context` interface so the single-Gemini baseline and later agents can use the same collection without depending on a particular agent framework. Share the completed local database as a versioned ZIP with a SHA-256 checksum in the team Drive; keep the generated database out of Git. Teammates can use the ZIP without re-embedding documents, but live queries still require Gemini API access for query embeddings. Answer generation is a separate step and model choice.

## Why

One source makes provenance clear and keeps clinical inputs separate from reference material. Matching document and query embeddings makes similarity search meaningful. A versioned collection and checked snapshot let teammates reproduce the same retrieval setup without consuming quota to rebuild the whole index.

## Alternatives considered

- **Keep MiniLM as the active index:** It worked as a temporary offline path, but the project has now completed the chosen Gemini embedding path. MiniLM and Gemini vectors cannot be mixed.
- **Combine additional datasets with MedlinePlus:** This could increase coverage, but would blur source roles and require a new review of provenance, cleaning, and retrieval quality.
- **Have everyone rebuild the index or host ChromaDB centrally:** Rebuilding uses API quota and time. A hosted service could simplify live sharing later, but the current team can use a checked local snapshot.

## Consequences

The current index contains 6,883 chunks from 1,979 cleaned MedlinePlus topics. Each teammate keeps a local copy; any corpus, chunking, or embedding-model change requires a newly versioned index and handoff. Gemini query embeddings require a key and available quota even after downloading the ZIP. Source links make results inspectable, but a complete index does not prove that every query retrieves relevant or safe medical information. Retrieval quality, including non-English queries, still needs evaluation.

## Follow-up

1. Have teammates download the ZIP and checksum, verify the hash and 6,883-record count, and run a live search using their own Gemini API access.
2. Review retrieved passages across medical topics and languages before treating retrieval quality as established.
3. If the source, splitter, or embedding model changes, build a new collection and snapshot and update this decision or record its replacement. Reconsider hosted ChromaDB if local copies become a coordination problem.
4. Connect future agents to the same retrieval interface and record any change to the source policy separately.

See the [Gemini index setup](../../data_pipeline/GEMINI_MEDLINEPLUS.md) and [retrieval interface](../../retrieval/README.md). The separate [single-Gemini baseline decision](ADR-001-september-single-model-baseline.md) defines how retrieved context is used for one answer.
