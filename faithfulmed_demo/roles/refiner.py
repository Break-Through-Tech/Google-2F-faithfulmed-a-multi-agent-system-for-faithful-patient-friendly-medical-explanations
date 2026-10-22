"""Deterministic, targeted Refiner helper for the first FaithfulMed slice.

The Verifier owns the clinical judgment and selects exact draft spans. This
helper validates all edits before applying any; it never rewrites other text.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


EDIT_CATEGORIES = frozenset({"unsupported", "contradictory"})


def run_refiner(
    draft: str, verdict: Mapping[str, Any] | str, source_report: str = ""
) -> str:
    """Return revised_draft, or raise ValueError for an unusable verdict.

    Contract: {"faithful": bool, "findings": [{"category": str,
    "start": int, "end": int, "original": str, "replacement": str,
    "reason": str, "source_quote": str}]}. Offsets are Python string indices
    into THIS draft, with an exclusive end. A replacement must equal its exact
    source quote; an empty replacement removes the flagged span. This first
    slice does not generate paraphrases or restore omissions automatically.
    """
    if not isinstance(draft, str) or not isinstance(source_report, str):
        raise ValueError("draft and source_report must be strings")
    if isinstance(verdict, str):
        try:
            verdict = json.loads(verdict)
        except json.JSONDecodeError as exc:
            raise ValueError("verdict must be a JSON object") from exc
    if not isinstance(verdict, Mapping):
        raise ValueError("verdict must be an object")
    if set(verdict) != {"faithful", "findings"}:
        raise ValueError("verdict requires exactly faithful and findings")
    faithful = verdict["faithful"]
    findings = verdict["findings"]
    if type(faithful) is not bool or not isinstance(findings, list):
        raise ValueError("faithful must be boolean and findings must be a list")
    if faithful:
        if findings:
            raise ValueError("a faithful verdict cannot contain findings")
        return draft
    if not findings:
        raise ValueError("an unfaithful verdict must explain its findings")

    edits = []
    fields = {"category", "start", "end", "original", "replacement", "reason", "source_quote"}
    for finding in findings:
        if not isinstance(finding, Mapping) or set(finding) != fields:
            raise ValueError("each finding must contain exactly the documented edit fields")
        category = finding["category"]
        if not isinstance(category, str) or category not in EDIT_CATEGORIES:
            raise ValueError("unsupported finding category; omission repair needs a later adapter")
        for field in ("original", "replacement", "reason", "source_quote"):
            if not isinstance(finding[field], str):
                raise ValueError(f"{field} must be a string")
        start, end = finding["start"], finding["end"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(draft):
            raise ValueError("finding offsets must select a nonempty span in draft")
        if draft[start:end] != finding["original"]:
            raise ValueError("stale finding: original does not match the selected draft span")
        if not finding["reason"].strip():
            raise ValueError("a finding requires a reason")
        replacement = finding["replacement"]
        quote = finding["source_quote"]
        if replacement:
            if not replacement.strip() or replacement != quote or quote not in source_report:
                raise ValueError("replacement must equal a nonempty exact source_report quote")
        elif quote:
            raise ValueError("deletions must use an empty source_quote")
        if replacement == finding["original"]:
            raise ValueError("a flagged edit must change its selected span")
        edits.append((start, end, replacement))

    edits.sort()
    for previous, current in zip(edits, edits[1:]):
        if current[0] < previous[1]:
            raise ValueError("findings must not overlap")
    revised_draft = draft
    for start, end, replacement in reversed(edits):
        revised_draft = revised_draft[:start] + replacement + revised_draft[end:]
    return revised_draft


def refine_state(state: Mapping[str, Any]) -> dict[str, str]:
    """Return an ADK session-state delta without mutating the input state.

    An orchestration wrapper can emit this delta through EventActions. Errors
    propagate so a malformed verdict cannot silently be reported as success.
    """
    return {"revised_draft": run_refiner(
        state["draft"], state["verdict"], state.get("source_report", "")
    )}
