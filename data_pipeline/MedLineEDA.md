# Exploratory Data Analysis: MedlinePlus Lay-Language Glossary

## 1. Data Assessment & Identified Issues
* **Missing Data:** Several XML entries lack definitions or contain empty `<full-summary>` tags. Some definitions are just short reference links (e.g., "See [Other Topic]").
* **Duplicate Entries:** There are occurrences of duplicate medical terms caused by terms being assigned to multiple XML category trees. 
* **Formatting Artifacts:** The raw text contains heavy XML/HTML tagging (like `<ul>`, `<p>`, `<br>`) and excessive whitespace/newlines from the nested data structure.
* **Length Constraints:** While most lay-language definitions are concise, several comprehensive health topics contain massive blocks of text. Passing these directly into the vector database risks diluting the embedding accuracy, meaning these long entries must be split into smaller "chunks".

## 2. Cleaning Instructions & Parsing Plan
1. **Extraction & Sanitization:** Parse the XML tree and use Regex to strip all HTML tags and normalize whitespace.
2. **Filter Nulls:** Drop any records where the definition string is shorter than 15 characters to eliminate dead links and empty tags.
3. **Deduplicate:** Drop records that share the exact same `Medical_Term` string.
4. **Text Chunking:** Identify any definitions exceeding 800 characters. Split these long definitions by sentence into smaller chunks so the semantic meaning remains dense for the RAG retriever. 

## 3. Preparation Pipeline Log
*(Here are sample metrics. Run the Python script to generate the exact numbers for this dataset)*
* **Original records extracted:** 1,050
* **After removing empty/invalid records:** 1,040
* **After removing duplicate terms:** 1,035
* **Records exceeding length limits (Chunked):** 180
* **Final chunks ready for vector store:** 1,320
