"""Run a live Extractor smoke test on a synthetic note."""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from faithfulmed_demo.roles.extractor import (
    ClinicalAtoms,
    create_extractor,
    validate_source_quotes,
)


async def main():
    # Load the key without printing it.
    load_dotenv(".env")
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    # Read the team's existing synthetic example.
    example_path = Path("baseline/examples/synthetic_chest_pain.json")
    example = json.loads(example_path.read_text())
    source_report = (
    "The patient has no allergy to penicillin. "
    "The patient takes metformin 500 mg twice daily."
)

    # Give the Extractor the original note through shared state.
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name="extractor_smoke",
        user_id="local_user",
        session_id="chest_pain",
        state={"source_report": source_report},
    )

    runner = Runner(
        agent=create_extractor("gemini-3.8-flash"),
        app_name="extractor_smoke",
        session_service=sessions,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text="Extract the facts from source_report.")],
    )

    response_text = ""

    # Run the actual ADK agent.
    async for event in runner.run_async(
        user_id="local_user",
        session_id="chest_pain",
        new_message=message,
    ):
        if event.is_final_response() and event.content:
            response_text = "".join(
                part.text
                for part in event.content.parts
                if part.text
            )

    if not response_text:
        raise RuntimeError("The Extractor returned no final response.")

    # Check the JSON structure and exact source quotes.
    result = ClinicalAtoms.model_validate_json(response_text)
    validate_source_quotes(source_report, result.root)
    allergy_atoms = [
        atom for atom in result.root
        if "penicillin" in atom.text.lower()
    ]
    assert allergy_atoms, "The penicillin allergy fact is missing."
    assert all(
        atom.assertion == "negated" for atom in allergy_atoms
    ), "The allergy negation was lost."

    assert any(
        "metformin" in atom.text.lower()
        and "500 mg" in atom.text
        and "twice daily" in atom.text.lower()
        for atom in result.root
    ), "The medication, dosage, or frequency was lost."

    print("Negation and dosage checks passed.")

    print("SOURCE:")
    print(source_report)
    print("\nEXTRACTED ATOMS:")
    print(result.model_dump_json(indent=2))
    print("\nSchema and source-quote checks passed.")


if __name__ == "__main__":
    asyncio.run(main())