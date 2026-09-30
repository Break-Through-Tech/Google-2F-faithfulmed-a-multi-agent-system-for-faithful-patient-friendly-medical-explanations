# Medical RAG Data Pipeline

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
