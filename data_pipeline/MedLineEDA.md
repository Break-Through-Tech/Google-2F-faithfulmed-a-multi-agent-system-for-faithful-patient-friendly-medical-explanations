# Exploratory Data Analysis: MedlinePlus Lay-Language Topics

This report uses the local `data/MedLineGlossary/mplus_topics_2026-09-23.xml` source. The counts below were measured from that file using the same cleaning rules as [the reusable export script](export_medlineplus_cleaned.py) and the same splitting rule as [the chunking script](chunk_medlineplus.py). They replace the earlier illustrative counts.

## 1. Data assessment and issues

- **Missing definitions:** The XML contains **2,033** health-topic entries. Four have no usable `<full-summary>` text after cleaning. No nonempty definition was only 1–15 characters long.
- **Repeated titles:** Of the **2,029** entries left after the length filter, **50** repeat a title already kept. The export keeps the first occurrence of each exact cleaned title.
- **Formatting:** Summaries contain XML/HTML structure and irregular whitespace. The parser extracts the text within each summary and normalizes whitespace before export.
- **Length:** The **1,979** retained definitions have a median length of **1,255 characters** and a maximum of **8,201**. **1,612** retained topics need more than one chunk under the 800-character rule. Long entries should not be stored as one search passage.
- **Languages and sources:** The retained topics include **1,002 English** and **977 Spanish** entries. All retained records have a source ID and MedlinePlus URL. The bilingual source needs separate retrieval-quality checks; these counts alone do not show that search works equally well in both languages.

## 2. Cleaning and parsing rules used

1. Read each XML `<health-topic>` title, ID, URL, and `<full-summary>` text; normalize whitespace.
2. Remove definitions of **15 characters or fewer** after cleaning. In this source snapshot, this removes the four empty summaries.
3. Keep the **first** entry for each exact cleaned title; remove later repeated titles.
4. Split each retained definition into non-overlapping passages of **at most 800 characters**, preferring sentence boundaries and then word boundaries. The chunker checks that joining the passages reproduces the cleaned definition exactly. Each chunk keeps its source ID, URL, title, and position.

## 3. Measured preparation counts

| Step | Entries/topics remaining | Removed or produced at this step |
| --- | ---: | ---: |
| Health-topic entries in the XML | 2,033 | — |
| After removing empty or ≤15-character definitions | 2,029 | 4 removed |
| After removing repeated cleaned titles | **1,979** | 50 removed |
| Topics split into multiple passages | 1,612 of the 1,979 | 367 stay as one passage |
| Final passages ready for embedding | **6,883** | 800 characters maximum per passage |

The existing `medlineplus_cleaned.jsonl` matches these export rules record for record, and the existing `medlineplus_chunks_800.jsonl` has **6,883** rows. To regenerate them from the repository root:

```powershell
python data_pipeline/export_medlineplus_cleaned.py
python data_pipeline/chunk_medlineplus.py
```

These counts describe data preparation, not retrieval relevance or medical accuracy. Inspect sample chunk boundaries and search results before treating the index as an evaluated knowledge base.
