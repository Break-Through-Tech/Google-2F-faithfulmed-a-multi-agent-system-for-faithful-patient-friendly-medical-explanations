"""Human-readable views of ADK state; no model calls or changed scoring rules."""

from html import escape
import json
import re
from urllib.parse import urlparse

from .pipeline import Snapshot, STAGES

LABELS = ("Receive report", "Extract facts", "Check quotes", "Write explanation",
          "Verify", "Refine", "Check readability")
_SENTENCE_END = re.compile(r"(?<=[.!?])(?=\s|$)")


def _medlineplus_url(value: object) -> str | None:
    url = str(value or "").strip()
    # Keep link destinations safe in both HTML and Markdown. Reject malformed
    # URLs rather than letting one bad source stop presentation of the result.
    if not url or re.search(r'[\s<>"\\()\x00-\x1f\x7f]', url):
        return None
    try:
        parsed = urlparse(url)
        if (parsed.scheme in ("https", "http") and parsed.hostname in (
                "medlineplus.gov", "www.medlineplus.gov")
                and parsed.username is None and parsed.password is None
                and parsed.port is None):
            return url
    except ValueError:
        pass
    return None


def _source_records(state: dict) -> tuple[list[dict], list[dict]]:
    """Keep only quotes actually in this report and usable background URLs."""
    report_quotes = []
    seen_quotes = set()
    report = state.get("source_report") or ""
    for atom in state.get("atoms") or []:
        quote = str(atom.get("source_quote") or "").strip()
        if quote and quote in report and quote not in seen_quotes:
            seen_quotes.add(quote)
            report_quotes.append({"quote": quote, "href": f"#report-quote-{len(report_quotes)}",
                                  "number": len(report_quotes) + 1})

    pages = []
    seen_urls = set()
    for row in state.get("retrieved_context") or []:
        metadata = row.get("metadata") or {}
        url = _medlineplus_url(metadata.get("source_url"))
        if url and url not in seen_urls:
            seen_urls.add(url)
            pages.append({
                "url": url,
                "title": str(metadata.get("title") or metadata.get("term") or "MedlinePlus passage"),
            })
    return report_quotes, pages


def _report_wording_match(text: str, report_quotes: list[dict]) -> dict | None:
    """A navigation shortcut for complete exact wording, not an entailment score."""
    for item in report_quotes:
        sentences = [part.strip() for part in _SENTENCE_END.split(item["quote"])]
        if text == item["quote"] or text in sentences:
            return item
    return None


def attributed_markdown(text: str, state: dict) -> str:
    """Append exact-wording shortcuts; never invent an evidence association.

    Preserve the original Markdown. Paraphrases and unmatched blocks stay
    unlinked. Retrieved background pages are listed separately in Sources.
    """
    report_quotes, _ = _source_records(state)
    if not text or not report_quotes:
        return text
    lines = []
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
        if in_code or not line.strip() or line.lstrip().startswith(("#", "```", "~~~")):
            lines.append(line)
            continue
        plain = re.sub(r'^\s*(?:[-+*]|\d+[.)])\s+', '', line).strip()
        plain = re.sub(r'^\*\*[^*\n]+:\*\*\s*', '', plain)
        # Bold/emphasis may surround exact source wording; do not rewrite its
        # words, negate it, drop qualifiers, or match only part of a claim.
        plain = plain.replace('**', '').replace('__', '')
        item = _report_wording_match(plain, report_quotes)
        if item:
            # The link is a separate marker, leaving bullets, headings and bold
            # labels intact. No nearest-source or first-source fallback exists.
            line = line.rstrip() + f" [Report quote {item['number']} (exact wording)]({item['href']})"
        lines.append(line)
    return "\n".join(lines)


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
        return "complete", prefix + "Explanation ready", "Automated checks found no outstanding issues in this run."
    if state.get("run_status") == "needs_simplification":
        return "review", prefix + "Draft needs simpler wording", state.get("suggestion") or "The draft did not meet the readability target."
    return "review", prefix + "Draft needs review", state.get("repair_blocker") or state.get("suggestion") or "Review the outstanding findings before using this explanation."


def status_html(view: Snapshot) -> str:
    kind, title, detail = result_status(view)
    if kind=='error':detail='The report could not be processed. See the engineering view for details.'
    return (f'<div class="result-status {kind}" role="status"><span class="status-dot"></span>'
            f'<div><strong>{escape(title)}</strong><p>{escape(detail)}</p></div></div>')


def answer_markdown(view: Snapshot) -> str:
    kind, _, _ = result_status(view)
    if kind == "complete":
        return attributed_markdown(view.state["final_answer"], view.state)
    if kind == "review":
        draft = view.state.get("revised_draft") or view.state.get("draft")
        return ("### Draft for review\n\n" + attributed_markdown(draft, view.state)
                if draft else "No explanation is available for this run.")
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
             (str(count) if count is not None else "—", "Unresolved findings", "Flagged by this run's Verifier check"),
             (str(len(facts)) if isinstance(facts, list) else "—", "Extracted facts", "Linked to source quotes")]
    return '<div class="metric-grid">' + "".join(
        f'<div class="metric"><strong>{escape(value)}</strong><span>{label}</span><small>{note}</small></div>'
        for value, label, note in cards) + '</div>'


def sources_html(state: dict) -> str:
    report_quotes, pages = _source_records(state)
    rows = state.get("retrieved_context") or []
    if not report_quotes and not rows:
        return '<p class="empty-note">Retrieved medical references will appear here.</p>'
    cards = []
    if report_quotes:
        cards.append('<p class="source-label">Original report quotes · exact wording, not independent clinical validation</p>')
        for index, item in enumerate(report_quotes):
            cards.append(
                f'<article id="report-quote-{index}" class="source-card">'
                f'<h4>Report quote {item["number"]}</h4><p>{escape(item["quote"])}</p></article>')
    background = []
    for row in rows:
        metadata = row.get("metadata") or {}
        title = escape(str(metadata.get("title") or metadata.get("term") or "MedlinePlus passage"))
        url = _medlineplus_url(metadata.get("source_url"))
        if url:
            title = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title} ↗</a>'
        background.append(f'<article class="source-card"><h4>{title}</h4><p>{escape(str(row.get("text", "")))}</p></article>')
    label = "Scripted reference passage" if state.get("mode") == "offline-scripted" else "Retrieved reference passages"
    if background:
        cards.append(f'<p class="source-label">{label} · general medical background; retrieval alone does not establish sentence support</p>')
        cards.extend(background)
    return "".join(cards)


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
            "faithfulness_recheck_required", "suggestion", "stage_modes", "error", "execution_trace")
    return {key: state[key] for key in keys if key in state}


def engineering_html(state: dict) -> str:
    rows=state.get('execution_trace',[])
    if not rows:return '<p class="empty-note">Run a report to see actual steps and calls here.</p>'
    labels={'stage':'Workflow step','model':'Gemini model call','retrieval':'Retrieval function',
            'local':'Local Python check/edit','scripted':'Scripted fixture'}
    parts=['<div class="execution-timeline" aria-label="Execution history">']
    for row in rows:
        duration=row.get('duration_ms')
        timing=f'{duration/1000:.2f} s' if isinstance(duration,(float,int)) else 'In progress'
        kind=labels.get(row.get('kind'),'Operation')
        details={k:row[k] for k in ('started_utc','inputs','output','error_type','service_code') if k in row}
        body=escape(json.dumps(details,ensure_ascii=False,indent=2))
        status=escape(str(row.get('status','unknown')))
        parts.append(f'<details class="execution-entry {"execution-stage" if row.get("kind")=="stage" else ""}">'
            f'<summary><strong>{escape(str(row.get("name","Operation")))}</strong>'
            f'<span>{escape(str(row.get("stage","")))} · {kind}</span>'
            f'<span class="execution-status">{status} · {timing}</span></summary>'
            f'<pre>{body}</pre></details>')
    parts.append('</div>')
    return ''.join(parts)
