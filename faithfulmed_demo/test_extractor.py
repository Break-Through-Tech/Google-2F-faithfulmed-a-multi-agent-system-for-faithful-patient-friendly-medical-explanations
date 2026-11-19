"""Run a live Extractor smoke test on a synthetic note."""

import asyncio
import os

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

    source_report = (
        "The patient has no allergy to penicillin. "
        "The patient takes metformin 500 mg twice daily. "
        "Noncontrast technique limits evaluation of the abdominal organs. "
        "Atenolol makes acute anaphylaxis harder to treat, "
        "but remains medically necessary at this time. "
        "No further problems were reported after discharge. "
        "An EpiPen was prescribed for an allergic reaction "
        "or a sensation of an impending allergic reaction. "
        "Proceed directly to the emergency room after EpiPen administration. "
        "The patient denies hypertension and kidney disorder. "
        "FINDINGS: An indeterminate left renal nodule is seen. "
        "IMPRESSION: An indeterminate left adrenal nodule is described."
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

    texts = [atom.text.lower() for atom in result.root]

    assert any(
        "noncontrast" in text and "limit" in text
        for text in texts
    ), "The examination limitation is missing."

    assert any(
        "atenolol" in text and "harder" in text
        for text in texts
    ), "The atenolol treatment risk is missing."

    assert any(
        "atenolol" in text and "medically necessary" in text
        for text in texts
    ), "The reason for continuing atenolol is missing."

    assert any(
        "no further problems" in text and "discharge" in text
        for text in texts
    ), "The post-discharge status is missing."

    assert any(
        "epipen" in text
        and "impending" in text
        and "allergic reaction" in text
        for text in texts
    ), "The EpiPen use conditions are missing."

    for condition in ("hypertension", "kidney disorder"):
        assert any(
            condition in atom.text.lower()
            and atom.assertion == "negated"
            and "denies" in atom.source_quote.lower()
            and condition in atom.source_quote.lower()
            for atom in result.root
        ), f"Negation or supporting context missing: {condition}"

    assert any(
        "findings" in text and "renal" in text
        for text in texts
    ), "The renal finding lost its source section."

    assert any(
        "impression" in text and "adrenal" in text
        for text in texts
    ), "The adrenal finding lost its source section."

    print("Additional synthetic coverage and quote-context checks passed.")

    print("Negation and dosage checks passed.")

    print("SOURCE:")
    print(source_report)
    print("\nEXTRACTED ATOMS:")
    print(result.model_dump_json(indent=2))
    print("\nSchema and source-quote checks passed.")


if __name__ == "__main__":
    asyncio.run(main())