"""Human-readable views of ADK state; no model calls or changed scoring rules."""

from html import escape
from urllib.parse import urlparse

from .pipeline import Snapshot, STAGES

LABELS = ("Receive report", "Extract facts", "Check quotes", "Write explanation",
          "Verify", "Refine", "Check readability")


def progress_html(view: Snapshot) -> str:
    chips = []
    for i, (stage, label) in enumerate(zip(STAGES, LABELS), 1):
        done = stage in view.completed
        active = stage == view.active and not view.finished
        failed = bool(view.error) and stage == view.active
        kind = "failed" if failed else "done" if done else "active" if active else "waiting"
        description = "stopped" if failed else "finished" if done else "in progress" if active else "waiting"
        symbol = "!" if failed else "✓" if done else str(i)
        chips.append(f'<div class="stage {kind}" aria-label="{label}: {description}">'
                     f'<span class="stage-number">{symbol}</span><span>{label}</span></div>')
    return '<div class="stage-track" aria-label="Workflow progress">' + "".join(chips) + '</div>'


def result_status(view: Snapshot):
    state = view.state
    offline = state.get("mode") == "offline-scripted"
    prefix = "Scripted walkthrough · " if offline else ""
    if view.error or state.get("run_status") == "failed":
        return "error", prefix + "Run stopped", view.error or "No final explanation was produced."
    if not view.finished:
        return "running", prefix + "Working on your report", "Each step appears below as the pipeline progresses."
    issues = state.get("final_verdict", {}).get("issues", [])
    if state.get("run_status") == "complete" and state.get("final_answer") and not issues and not state.get("repair_blocker"):
        return "complete", prefix + "Explanation ready", "No unresolved findings in this run. The Verifier is still being calibrated."
    if state.get("run_status") == "needs_simplification":
        return "review", prefix + "Draft needs simpler wording", state.get("suggestion") or "The draft did not meet the readability target."
    return "review", prefix + "Draft needs review", state.get("repair_blocker") or state.get("suggestion") or "Review the outstanding findings before using this explanation."


def status_html(view: Snapshot) -> str:
    kind, title, detail = result_status(view)
    return (f'<div class="result-status {kind}" role="status"><span class="status-dot"></span>'
            f'<div><strong>{escape(title)}</strong><p>{escape(detail)}</p></div></div>')


def answer_markdown(view: Snapshot) -> str:
    kind, _, _ = result_status(view)
    if kind == "complete":
        return view.state["final_answer"]
    if kind == "review":
        draft = view.state.get("revised_draft") or view.state.get("draft")
        return "### Draft for review\n\n" + draft if draft else "No explanation is available for this run."
    if kind == "error":
        return "No final explanation was produced. Check the status message above."
    return "Your explanation will appear here when the checks finish."


def metrics_html(view: Snapshot) -> str:
    state = view.state
    score = state.get("readability_score") or {}
    grade = score.get("flesch_kincaid_grade")
    grade_text = f"{grade:.2f}" if isinstance(grade, (int, float)) else "—"
    passed = state.get("readability_status") == "passed"
    grade_note = "Meets grade-8 target" if passed else "Target: grade 8 or below"
    verdict = state.get("final_verdict")
    count = len(verdict.get("issues", [])) if isinstance(verdict, dict) and "issues" in verdict else None
    facts = state.get("atoms")
    cards = [(grade_text, "Reading grade", grade_note),
             (str(count) if count is not None else "—", "Unresolved findings", "Model check · uncalibrated"),
             (str(len(facts)) if isinstance(facts, list) else "—", "Extracted facts", "Linked to source quotes")]
    return '<div class="metric-grid">' + "".join(
        f'<div class="metric"><strong>{escape(value)}</strong><span>{label}</span><small>{note}</small></div>'
        for value, label, note in cards) + '</div>'


def sources_html(state: dict) -> str:
    rows = state.get("retrieved_context") or []
    if not rows:
        return '<p class="empty-note">Retrieved medical references will appear here.</p>'
    cards = []
    for row in rows:
        metadata = row.get("metadata") or {}
        title = escape(str(metadata.get("title") or metadata.get("term") or "MedlinePlus passage"))
        url = str(metadata.get("source_url") or "")
        parsed = urlparse(url)
        if parsed.scheme in ("https", "http") and parsed.hostname in ("medlineplus.gov", "www.medlineplus.gov"):
            title = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title} ↗</a>'
        cards.append(f'<article class="source-card"><h4>{title}</h4><p>{escape(str(row.get("text", "")))}</p></article>')
    label = "Scripted reference passage" if state.get("mode") == "offline-scripted" else "Retrieved reference passages"
    return f'<p class="source-label">{label} · general medical background</p>' + "".join(cards)


def facts_rows(state: dict) -> list:
    atoms = state.get("atoms")
    if not isinstance(atoms, list):
        return []
    return [[str(atom.get(key, "")) for key in ("text", "assertion", "source_quote")] for atom in atoms]


def checks_markdown(state: dict) -> str:
    if not state.get("verdict"):
        return "Verification and repair details will appear after those steps run."
    initial = state["verdict"].get("issues", [])
    final = state.get("final_verdict", {}).get("issues", [])
    history = state.get("refinement_history", [])
    lines = [f"**Initial findings:** {len(initial)} · **Repair rounds:** {len(history)}",
             "The Refiner makes permitted exact edits, then the Verifier checks again. At most two rounds are allowed."]
    for title, issues in (("Initial findings", initial), ("Remaining findings", final)):
        lines.append(f"### {title}")
        if not issues:
            lines.append("None recorded." if title == "Initial findings" or "final_verdict" in state else "Recheck pending.")
        for issue in issues:
            # Escape markup from model-provided issue fields.
            lines.append(f"- **{escape(str(issue.get('category', 'Finding')))}:** {escape(str(issue.get('reason', '')))}")
            if issue.get("claim"):
                lines.append("  Flagged text: " + escape(str(issue["claim"])))
    if state.get("repair_blocker"):
        lines.append("**Why review is needed:** " + escape(state["repair_blocker"]))
    if state.get("suggestion"):
        lines.append("**Readability suggestion:** " + escape(state["suggestion"]))
    rewrites = state.get("readability_history", [])
    if rewrites:
        lines.append(f"### Readability rewrites ({len(rewrites)}/2)")
        for item in rewrites:
            before = item['before_score'].get('flesch_kincaid_grade')
            after = (item.get('after_score') or {}).get('flesch_kincaid_grade')
            verdict = item.get('verdict')
            outcome = ('Verifier recheck pending' if verdict is None else
                       'accepted after recheck' if item['accepted'] else 'not accepted')
            lines.append(f"- Attempt {item['round']}: grade {before} → {after}; {outcome}.")
            if verdict:
                for issue in verdict.get('issues', []):
                    lines.append("  Finding: " + escape(str(issue.get('reason', 'Review required.'))))
            if item.get('stop_reason'):
                lines.append("  " + escape(item['stop_reason']))
    return "\n\n".join(lines)


def trace_state(state: dict) -> dict:
    """Expose known workflow fields only, never arbitrary session metadata."""
    keys = ("source_report", "mode", "model", "run_status", "atoms", "retrieval_query", "retrieved_context",
            "draft", "verdict", "revised_draft", "final_verdict", "refinement_history", "repair_blocker",
            "final_answer", "readability_status", "readability_score", "readability_history",
            "faithfulness_recheck_required", "suggestion", "stage_modes", "error")
    return {key: state[key] for key in keys if key in state}
