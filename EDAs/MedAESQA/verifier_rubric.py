"""Deterministic faithfulness categories derived from MedAESQA annotations."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

FULLY_SUPPORTED = "fully_supported"
UNREFERENCED = "unreferenced"
NEUTRAL = "neutral"
IRRELEVANT = "irrelevant_evidence"
INVALID = "invalid_citation"
CONTRADICTORY = "contradictory"
WEAK = "weakly_supported"

_SEVERE_RELATIONS = (CONTRADICTORY, INVALID, IRRELEVANT, NEUTRAL)
_RELATION_TO_CATEGORY = {
    "supporting": "supporting",
    "neutral": NEUTRAL,
    "not relevant": IRRELEVANT,
    "invalid citation": INVALID,
    "contradicting": CONTRADICTORY,
}


def classify_sentence(
    sentence_relevance: str | None,
    citations: Iterable[Mapping[str, Any]] | None,
) -> str:
    """Classify one sentence using its MedAESQA relevance and citations.

    The precedence intentionally treats contradiction as the strongest failure,
    followed by invalid, irrelevant, and neutral evidence. A sentence without
    citations is unreferenced, even when its text may be medically correct.
    """
    citation_list = list(citations or [])
    if not citation_list:
        return UNREFERENCED

    relations = {
        _RELATION_TO_CATEGORY.get(
            _normalize_relation(citation.get("evidence_relation")),
            _normalize_relation(citation.get("evidence_relation")),
        )
        for citation in citation_list
    }
    for category in _SEVERE_RELATIONS:
        if category in relations:
            return category

    if relations == {"supporting"} and sentence_relevance == "required":
        return FULLY_SUPPORTED
    return WEAK


def classify_answer(sentences: Iterable[Mapping[str, Any]]) -> str:
    """Return the highest-risk rubric category found in an answer.

    Categories are ordered from most serious to least serious. This is a
    transparent baseline rule for analysis, not a replacement for human review.
    """
    sentence_categories = [
        classify_sentence(
            sentence.get("answer_sentence_relevance"),
            sentence.get("citation_assessment"),
        )
        for sentence in sentences
    ]
    priority = [CONTRADICTORY, INVALID, IRRELEVANT, NEUTRAL, UNREFERENCED, WEAK]
    for category in priority:
        if category in sentence_categories:
            return category
    return FULLY_SUPPORTED


def _normalize_relation(relation: Any) -> str:
    """Normalize dataset relation text without changing its meaning."""
    return str(relation or "").strip().lower()