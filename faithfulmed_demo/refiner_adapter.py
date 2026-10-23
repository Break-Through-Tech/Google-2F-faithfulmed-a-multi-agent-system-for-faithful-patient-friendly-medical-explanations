"""Translate demo Verifier findings into Zurabi's strict Refiner contract."""

from .roles.refiner import run_refiner


def apply_verified_edits(draft: str, verdict: dict, source_report: str) -> str:
    """Apply all supported exact edits, or raise ValueError before any edit."""
    issues = verdict.get("issues")
    if not isinstance(issues, list):
        raise ValueError("Verifier did not return an issues list")
    if not issues:
        return run_refiner(draft, {"faithful": True, "findings": []}, source_report)

    findings = []
    for issue in issues:
        category = issue.get("category")
        if category == "omission":
            raise ValueError("Omission requires human review; automatic insertion is unsupported")
        if category not in ("unsupported", "contradiction"):
            raise ValueError("Unknown finding category requires review")
        original = issue.get("claim", "")
        replacement = issue.get("replacement", "")
        quote = issue.get("source_quote", "")
        if not isinstance(original, str) or not original or draft.count(original) != 1:
            raise ValueError("Finding must identify one exact draft span")
        if not isinstance(replacement, str) or not isinstance(quote, str):
            raise ValueError("Replacement and quote must be text")
        # Zurabi's helper permits only deletion or an exact source quote.
        if replacement and (replacement != quote or quote not in source_report):
            raise ValueError("Proposed replacement is not an exact source quote")
        start = draft.index(original)
        findings.append({
            "category": "contradictory" if category == "contradiction" else "unsupported",
            "start": start, "end": start + len(original), "original": original,
            "replacement": replacement, "reason": issue.get("reason", ""),
            "source_quote": quote if replacement else "",
        })
    revised = run_refiner(draft, {"faithful": False, "findings": findings}, source_report)
    if not revised.strip():
        raise ValueError("Repair would leave an empty explanation")
    return revised
