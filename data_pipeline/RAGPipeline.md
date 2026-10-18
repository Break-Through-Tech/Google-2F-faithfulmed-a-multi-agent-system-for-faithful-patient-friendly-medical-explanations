# MedlinePlus RAG pipeline

The active pipeline uses only the cleaned MedlinePlus topics. It exports 1,979
topics, splits them into 6,883 traceable chunks, and stores their
`gemini-embedding-2` vectors in ChromaDB. See [the Gemini setup and handoff](GEMINI_MEDLINEPLUS.md)
for the commands, index location, and prepared database ZIP.

Ruhma's earlier multi-source RAG notebook and its generated embedding JSONL
were exploratory handoff artifacts. They were retired after the MedlinePlus-only
Gemini index was completed; their original versions remain in Git history.
