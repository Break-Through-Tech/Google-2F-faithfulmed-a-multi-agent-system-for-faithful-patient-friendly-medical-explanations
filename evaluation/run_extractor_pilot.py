"""Run only the Extractor on saved pilot source reports.

Makes one live Gemini request per selected report.
Original traces are read only. Each run gets a new output folder.
"""

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from faithfulmed_demo.roles.extractor import (
    ClinicalAtoms,
    EXTRACTOR_INSTRUCTION,
    create_extractor,
    validate_source_quotes,
)

PILOT_IDS = (4998, 3938, 3808, 3606, 2964)

TRACE_DIR = Path(
    "data/comparison_results/"
    "five_report_readability_2026-11-08_v2/traces"
)


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def extract_report(report_id, source, model):
    sessions = InMemorySessionService()
    session_id = f"report_{report_id}"

    await sessions.create_session(
        app_name="extractor_pilot",
        user_id="local_user",
        session_id=session_id,
        state={"source_report": source},
    )

    runner = Runner(
        agent=create_extractor(model),
        app_name="extractor_pilot",
        session_service=sessions,
    )

    response = ""
    async for event in runner.run_async(
        user_id="local_user",
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[
                types.Part(
                    text="Extract the facts from source_report."
                )
            ],
        ),
    ):
        if event.is_final_response() and event.content:
            response = "".join(
                part.text or ""
                for part in (event.content.parts or [])
            )

    if not response:
        raise RuntimeError("Extractor returned no final response.")

    return response


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ids", nargs="+", type=int, default=list(PILOT_IDS)
    )
    parser.add_argument("--model", default="gemini-3.8-flash")
    args = parser.parse_args()

    if len(args.ids) != len(set(args.ids)):
        parser.error("Report IDs must not be repeated.")

    unknown = set(args.ids) - set(PILOT_IDS)
    if unknown:
        parser.error(f"Unknown pilot IDs: {sorted(unknown)}")

    # Validate every selected input before making any API requests.
    inputs = []
    for report_id in args.ids:
        paths = list(TRACE_DIR.glob(f"row{report_id}-adk-*.json"))
        if len(paths) != 1:
            raise RuntimeError(
                f"Expected one saved trace for {report_id}; "
                f"found {len(paths)}."
            )

        original = json.loads(paths[0].read_text(encoding="utf-8"))
        source = original["state"]["source_report"]
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Empty or invalid source: {report_id}")

        inputs.append((report_id, paths[0], source))

    load_dotenv(".env")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY in your root .env file.")
    os.environ["GOOGLE_API_KEY"] = key

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = Path("data/extractor_reruns") / stamp
    output_dir.mkdir(parents=True, exist_ok=False)

    print(f"Output folder: {output_dir}", flush=True)

    for report_id, original_path, source in inputs:
        payload = {
            "report_id": report_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "temperature": 0,
            "original_trace": str(original_path),
            "source_sha256": sha256(source),
            "instruction_sha256": sha256(EXTRACTOR_INSTRUCTION),
            "instruction": EXTRACTOR_INSTRUCTION,
            "status": "started",
            "state": {"source_report": source},
        }
        output_path = output_dir / f"{report_id}.json"

        try:
            print(f"Extracting report {report_id}...", flush=True)
            response = await extract_report(
                report_id, source, args.model
            )
            payload["raw_response"] = response

            atoms = ClinicalAtoms.model_validate_json(response)
            payload["state"]["atoms"] = atoms.model_dump()
            validate_source_quotes(source, atoms.root)

            payload["status"] = "schema_and_quotes_passed"
            payload["semantic_review"] = "pending"
        except ValueError as exc:
            payload["status"] = "validation_failed"
            payload["error"] = f"{type(exc).__name__}: {exc}"
            print(
                f"Report {report_id} failed validation; "
                "saving the result and continuing.",
                flush=True,
            )
        except Exception as exc:
            payload["status"] = "failed"
            payload["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            output_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        print(f"Saved {output_path}", flush=True)

    print("Finished. Meaning and coverage still require review.")


if __name__ == "__main__":
    asyncio.run(main())