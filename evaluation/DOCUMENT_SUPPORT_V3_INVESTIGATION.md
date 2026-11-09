# Investigation of the revised development run

This is an offline inspection of the saved v2/v3 predictions and cached source abstracts. It makes no new service calls, changes no labels or scores, and does not resolve reference disagreements by selecting whichever label matches the model. The source files are listed in the [v3 run record](DOCUMENT_SUPPORT_V3_RUN.md).

## What changed

There are 24 cases successfully scored by both runs. The previous run matched 16 references; the revised run matched 15. Exactly three citation-support decisions changed. All other matched cases retained the same binary decision, although their proposition inventories or reasons may differ.

| Question / PMID | Previous to revised | Evidence-based interpretation |
| --- | --- | --- |
| 126 / 33484483 | no support to support; reference neutral | The new response interprets disjunction/nondisjunction and aneuploidy as their plain-language equivalents and marks the definition supported. The supplied human review also marked this case supported. That is consistent with the new paraphrase instruction but reduces agreement with the neutral reference. It is not evidence that the prompt change simply made the judge worse. The extent of support for the whole definition remains a matter of scope. |
| 126 / 17911163 | no support to support; reference supporting | The revised response accepts the general maternal-age association but keeps the specific claim about the age effect predominating in meiosis I as not established. This aligns better with the selected reference and distinguishes partial coverage. The inference still links related statements in the abstract rather than quoting the exact answer wording. |
| 150 / 20397860 | support to no support; reference supporting | The abstract describes one patient treated with extension exercises and later added traction. Symptoms improved. The new response rejects general effectiveness of exercise alone because the combined intervention and isolated case do not establish that claim. This follows the new scope/causality warnings. However, the answer says treatments "can" help, which is weaker than proving general or independent efficacy. The prompt may encourage an overly demanding evidence standard for citation relevance. This is a plausible task-definition disagreement, not an established reference correction. |

These changes reflect a tradeoff: allowing paraphrases while demanding stronger population and intervention evidence can move decisions in opposite directions. The v3 score therefore cannot diagnose a single defect, and there is no evidence from this one run that another broad prompt rewrite would solve the problem.

## Four exact-quote failures

| Question / PMID | First attempt | One retry | What is known |
| --- | --- | --- | --- |
| 148 / 18481559 | quote not verbatim | valid response | Recovered with the same input and settings; final citation decision remained support. |
| 126 / 17314397 | quote not verbatim | valid response | Recovered; final citation decision remained support. |
| 126 / 15329821 | quote not verbatim | quote not verbatim | Still unscored. The source contains direct maternal-age/oocyte evidence; this is a formatting/anchoring failure category, not a negative support decision. |
| 138 / 15236629 | quote not verbatim | quote not verbatim | Still unscored. The source connects oral pseudoephedrine with Sudafed but does not address Afrin. V2 also failed this case, without a detailed error category. |

The new categories identify the failing check, but the rejected quote text and proposition index were not retained. We cannot reconstruct whether a quote omitted intervening text, changed punctuation/spacing, altered words, or made another error. The successful retries establish recoverability for two cases, not the exact cause of their first failures. Do not silently relax substring validation or retrospectively count these cases as correct.

The instruction to quote a continuous span may produce longer quotes and increase copying demands, but this is a hypothesis, not a demonstrated cause: prompts changed in several ways, and model outputs can vary even at temperature 0.

## Practical next step

The [numbered-passage implementation](DOCUMENT_SUPPORT_SPANS.md) is now prepared and locally tested. It has not yet been evaluated with live Gemini responses.

Fix evidence anchoring as a separate engineering task before spending more calls on broad prompt tuning. A useful design is to supply versioned, numbered source spans, have the judge reference their IDs, and have Python copy their exact source text. This would remove the need for the model to reproduce long passages character for character. Span boundaries and context must be preserved; an existing ID would still not prove semantic support, and the new format would need its own version and local tests. Alternatively, safe structured diagnostics could capture which proposition failed and non-text comparison facts, rather than discarding all diagnostic information.

For the accuracy target, stop treating the original reference score as an unquestioned measure of the new document-level task. Keep reporting it, including disagreements, but clarify which task and evidence scope the project expects. A small human-reviewed, task-matched development reference can help validate that distinction; the existing human review already exposes one mismatch. It does not make all current labels authoritative or validate the held-out set.

After the anchoring change and a fixed task definition, make one bounded, versioned development check. Do not repeatedly revise the prompt to fit these same references or start tuning on the held-out examples. Neither the engineering change nor this review establishes that the 80% / 0.6 targets are met.

Machine-readable comparison: `data/calibration_results/document_support_v3_investigation.json`. Historical scores remain 68% / 0.31 for v2 and 62.5% / 0.18 for v3, with different scored coverage.
