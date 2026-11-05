"""Review saved Extractor outputs for the five fixed pilot reports.

No API calls. Does not modify frozen reports or the Extractor.
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PILOT_IDS = ["4998", "3938", "3808", "3606", "2964"]

CHECKS = {
    "negation": "Are negative statements preserved?",
    "laterality": "Are left/right and body locations preserved?",
    "measurements": "Are numbers, doses, frequencies, and units preserved?",
    "uncertainty": "Are uncertainty and pending results preserved?",
    "plans": "Are conditional plans distinguished from completed actions?",
    "coverage": "Are important facts present without invented patient facts?",
}


def digest(text):
    """Fingerprint the exact source text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ask_choice(question, choices):
    """Require an explicit review decision."""
    while True:
        answer = input(f"{question} [{'/'.join(choices)}]: ").strip().lower()
        if answer in choices:
            return answer
        print("Please enter one of:", ", ".join(choices))


def markdown_cell(value):
    """Keep reviewer notes inside one Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def load_atoms(trace_path, source_report):
    """Read the existing smoke-trace format or an exported ADK state."""
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    state = payload.get("state", payload)

    # Require matching original text, rather than trusting a filename.
    if state.get("source_report") != source_report:
        raise ValueError(
            "Trace source_report does not exactly match the frozen report."
        )

    atoms = state.get("atoms")
    if isinstance(atoms, str):
        atoms = json.loads(atoms)

    if not isinstance(atoms, list) or not atoms:
        raise ValueError("Trace must contain a nonempty atoms list.")

    allowed_assertions = {
        "affirmed", "negated", "uncertain", "pending", "conditional"
    }
    allowed_types = {
        "symptom", "diagnosis", "medication",
        "lab_value", "procedure", "instruction"
    }

    for number, atom in enumerate(atoms, start=1):
        if not isinstance(atom, dict):
            raise ValueError(f"Atom {number} is not an object.")

        for field in ("text", "type", "assertion", "source_quote"):
            if not isinstance(atom.get(field), str) or not atom[field].strip():
                raise ValueError(f"Atom {number}: missing/empty {field}.")

        if atom["type"] not in allowed_types:
            raise ValueError(f"Atom {number}: invalid type.")

        if atom["assertion"] not in allowed_assertions:
            raise ValueError(f"Atom {number}: invalid assertion.")

        if atom["source_quote"] not in source_report:
            raise ValueError(f"Atom {number}: quote absent from source.")

    return atoms


def write_report(reviews, output):
    """Save progress after every report, including blocked reviews."""
    lines = [
        "# Extractor pilot checks",
        "",
        "Owner: Vaibhavi Srivastava",
        "",
        "Automated checks validate structure and exact source quotes.",
        "Meaning and coverage decisions are manual source-to-atom reviews.",
        "These reviews are not the evaluator's gold key-fact inventories.",
        "",
        "| Source ID | Source SHA-256 | Trace SHA-256 | Review status |",
        "| --- | --- | --- | --- |",
    ]

    for source_id in PILOT_IDS:
        review = reviews.get(source_id, {})
        lines.append(
            f"| {source_id} | {review.get('source_sha256', '')} "
            f"| {review.get('trace_sha256', '')} "
            f"| {review.get('status', 'not reviewed')} |"
        )

    for source_id in PILOT_IDS:
        if source_id not in reviews:
            continue

        review = reviews[source_id]
        lines.extend([
            "",
            f"## Report {source_id}",
            "",
            f"Reviewed at: {review['reviewed_at']}",
            "",
            "| Check | Result | Evidence / issue |",
            "| --- | --- | --- |",
        ])

        for check, result in review["checks"].items():
            lines.append(
                f"| {check} | {result['result']} "
                f"| {markdown_cell(result['evidence'])} |"
            )

    lines.extend([
        "",
        "## Setup reproduction",
        "",
        "Record the actual second-computer setup result here:",
        "",
        "- Computer / OS: not recorded",
        "- Python and dependency versions: not recorded",
        "- Shared database snapshot / checksum: not recorded",
        "- Offline walkthrough result: not recorded",
        "- Live example result or blocker: not recorded",
        "- Setup problems and resolutions: not recorded",
        "",
        "Completion requires all five reviews and the setup result.",
        "",
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument(
        "--reports", type=Path,
        default=Path("data/curated_baseline/mtsamples_curated_50.csv"),
    )
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/curated_baseline/freeze_manifest.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("evaluation/EXTRACTOR_CHECK.md"),
    )
    args = parser.parse_args()

    # Preserve an existing review instead of overwriting someone's work.
    if args.output.exists():
        raise SystemExit(
            f"{args.output} already exists. Use --output with a new filename."
        )

    with args.reports.open(encoding="utf-8-sig", newline="") as handle:
        reports = {
            row["source_row_id"]: row["transcription"]
            for row in csv.DictReader(handle)
        }

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected_hashes = manifest["transcription_sha256"]

    # Verify all five inputs before beginning a review.
    for source_id in PILOT_IDS:
        if source_id not in reports:
            raise SystemExit(f"Frozen report {source_id} is missing.")
        if digest(reports[source_id]) != expected_hashes[source_id]:
            raise SystemExit(f"Frozen report {source_id} has changed.")

    reviews = {}

    for source_id in PILOT_IDS:
        source_report = reports[source_id]
        trace_path = args.traces / f"{source_id}.json"
        review = {
            "source_sha256": digest(source_report),
            "trace_sha256": "",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "status": "blocked",
            "checks": {},
        }

        try:
            trace_bytes = trace_path.read_bytes()
            review["trace_sha256"] = hashlib.sha256(trace_bytes).hexdigest()
            atoms = load_atoms(trace_path, source_report)
        except (OSError, ValueError, TypeError, AttributeError) as error:
            review["checks"]["structure and exact quotes"] = {
                "result": "blocked",
                "evidence": str(error),
            }
            reviews[source_id] = review
            write_report(reviews, args.output)
            print(f"\nReport {source_id} blocked: {error}")
            continue

        print(f"\nREPORT {source_id}\n")
        print(source_report)
        print("\nEXTRACTED ATOMS\n")

        for number, atom in enumerate(atoms, start=1):
            print(
                f"{number}. [{atom['type']} / {atom['assertion']}] "
                f"{atom['text']}"
            )
            print(f"   SOURCE QUOTE: {atom['source_quote']}\n")

        print(
            "Read the whole source and compare it with every atom. "
            "Also inspect its existing source-review caveats."
        )

        review["checks"]["structure and exact quotes"] = {
            "result": "pass",
            "evidence": f"Validated {len(atoms)} atoms against frozen text.",
        }

        for check, question in CHECKS.items():
            decision = ask_choice(
                question, ["pass", "issue", "na", "pending"]
            )
            evidence = ""
            while not evidence.strip():
                evidence = input(
                    "Give a precise source/atom example, issue, "
                    "or reason this is not applicable: "
                )

            review["checks"][check] = {
                "result": decision,
                "evidence": evidence,
            }

        decisions = [
            result["result"] for result in review["checks"].values()
        ]
        if "pending" in decisions:
            review["status"] = "pending"
        elif "issue" in decisions:
            review["status"] = "issue"
        else:
            review["status"] = "pass"

        reviews[source_id] = review
        write_report(reviews, args.output)
        print(f"Saved review for {source_id}.")

    print(f"\nReport saved: {args.output}")
    print("Setup reproduction must still be recorded separately.")


if __name__ == "__main__":
    main()