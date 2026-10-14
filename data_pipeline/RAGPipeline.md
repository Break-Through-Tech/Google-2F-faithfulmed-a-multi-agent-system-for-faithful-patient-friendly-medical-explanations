# Medical RAG Data Pipeline

> **Temporary local retrieval:** [MINILM_MEDLINEPLUS.md](MINILM_MEDLINEPLUS.md)
> builds a separate MiniLM index from the current cleaned MedlinePlus chunks
> while the Gemini build is limited by daily quota. Both use the same chunk file.

> **Historical notebook description:** This page describes Ruhma's earlier
> multi-source pipeline. The current MedlinePlus-only, chunked Gemini route is
> documented in [GEMINI_MEDLINEPLUS.md](GEMINI_MEDLINEPLUS.md). The earlier
> `text-embedding-004` references below are obsolete; Google shut that model
> down in January 2026. The supplied older embeddings file contains MiniLM
> vectors and is not used by the new Gemini collection.

This folder contains the data aggregation and processing pipeline for the Medical RAG system. The primary notebook merges three medical terminology datasets, cleans the data, and generates vector embeddings using Google's Gemini API.

## Workflow Overview
1. **Data Ingestion:** Extracts and parses XML/CSV data from MedlinePlus, MedQuAD, and PLABA.
2. **Cleaning & Filtering:** Strips XML namespaces and filters for English-only content.
3. **Embedding Generation:** Batches the concatenated Q&A pairs/definitions and runs them through the `text-embedding-004` model.
4. **Storage:** Writes the vectorized dataset to Google Drive in JSONL format for database ingestion.

## Prerequisites
* **Environment:** Google Colab (with Google Drive mounted).
* **Dependencies:** `google-generativeai`, `pandas`
* **Authentication:** A valid Gemini API key must be saved in Colab's built-in Secrets manager under the name `GEMINI_API_KEY`.

## Input Data
The script expects the following raw files to be stored in a Google Drive folder named `FaithfulMed Data Simplifier` inside `Google 2F - FaithfulMed`:
* `MedLineGlossary.zip` (English health topics)
* `MedQuAD.zip` (English GitHub repository)
* `PLABA.zip` (or the PLABA CSV file)

## Output
* `RAG_Embeddings_Full.jsonl` - A master dataset of ~50,000 records containing the medical terms, plain-language definitions, source metadata, and Gemini vector embeddings. This file is ready to be loaded directly into ChromaDB.
