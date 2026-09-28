
# MedAESQA Dataset Exploratory Data Analysis (EDA)

This folder contains the exploratory data analysis on the MedAESQA dataset. The analysis helps us understand the structure of the data, evaluate the faithfulness and quality of machine-generated medical answers, and establish a quantitative evaluation rubric.

## 1. Dataset Analyzed

The `MedAESQA` (Medical Answer Evaluation and Sentence Quality Assessment) dataset (`medaesqa_v1.json`) was analyzed. It contains human expert evaluations of machine-generated answers to medical questions, including sentence-by-sentence relevance tags and precise citation-to-evidence mappings.

## 2. Why We Analyzed It

This analysis is a crucial step for the **Verifier agent** in the FaithfulMed project. The goals are to:
- Programmatically understand the dataset's nested structure.
- Evaluate factual alignment and identify potential hallucinations in machine-generated medical explanations.
- Identify patterns in answer accuracy, sentence relevance, and citation relations.
- Extract concrete examples to design a quantitative faithfulness and hallucination rubric.

## 3. What this Folder Contains

- `MedAESQA_EDA.ipynb`: The primary Jupyter Notebook executing the analysis pipeline.
- `README.md`: This file, providing an overview of the exploratory analysis.
- `verifier_rubric.py`: A deterministic, reusable baseline rubric for classifying sentence- and answer-level evidence patterns.
- `test_verifier_rubric.py`: Tests for the reusable rubric categories and precedence rules.

The notebook now includes a category-specific example extraction cell for fully supported, unreferenced, irrelevant, neutral, invalid-citation, and contradictory cases.

## 4. Key Findings

- **Overall Answer Accuracy**: Machine-generated answers show high overall accuracy, with **91.83%** of answers classified as accurate.
- **Sentence Relevance**: **76.68%** of the generated sentences are deemed `required`, while **13.52%** are `unnecessary`.
- **Evidence Relations**: Out of 9,611 citations analyzed:
    - **67.53%** are `supporting`.
    - **22.37%** present verification issues: **16.14%** are `not relevant`, **4.26%** are `invalid citations`, and **1.97%** are `contradicting`.
    These statistics emphasize the need for a granular citation verification pipeline, even for answers marked as globally accurate.

## 5. Verifier Foundation

The EDA supports the first Verifier foundation with six transparent categories:

- `fully_supported`: required sentence with only supporting evidence.
- `unreferenced`: sentence with no citation assessments.
- `neutral`: at least one neutral evidence relation.
- `irrelevant_evidence`: at least one `not relevant` relation.
- `invalid_citation`: at least one invalid citation relation.
- `contradictory`: at least one contradicting relation.

Sentences with supporting evidence but non-required relevance, or other mixed cases not covered above, are classified as `weakly_supported`. For answer-level classification, the highest-risk category is retained. This is a deterministic baseline for analysis and calibration, not a substitute for human review or an LLM judge.

Run the rubric tests from the repository root with:

```text
python -m unittest discover -s EDAs/MedAESQA -p "test_*.py" -v
```

## 6. How to Run the Notebook

1. Ensure the raw `medaesqa_v1.json` dataset is available from `data/MedAESQA_data/medaesqa_v1.json` in this repository, or alongside the notebook when using Colab.
2. Open `MedAESQA_EDA.ipynb` in your Jupyter environment or Google Colab.
3. Run the cells sequentially to parse the data, calculate statistics, and display the distribution plots.

## 7. Raw Dataset Source

The `medaesqa_v1.json` dataset is a curated benchmark for medical answer sentence-level evaluation, mapping LLM generations to verified PubMed articles (PMIDs) for ground-truth comparison.
