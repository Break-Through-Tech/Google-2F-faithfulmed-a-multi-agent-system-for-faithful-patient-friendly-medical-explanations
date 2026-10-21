"""FaithfulMed ADK entry point for `adk web .` (placeholder stages only).

State flow: source_report -> atoms -> retrieved_context -> draft -> verdict
-> revised_draft -> final_answer. Each placeholder uses the name and output
key of the real agent that will replace it.
"""

import os
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from google.adk.agents import BaseAgent, InvocationContext, SequentialAgent
from google.adk.events import Event, EventActions
from google.genai import types

# Load the key without printing it. A missing .env or key is fine here.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def _message(
    ctx: InvocationContext,
    author: str,
    text: str,
    state_delta: Optional[dict[str, Any]] = None,
) -> Event:
    """Build a chat event, optionally saving fields to session state."""

    return Event(
        invocation_id=ctx.invocation_id,
        author=author,
        branch=ctx.branch,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
    )


class Intake(BaseAgent):
    """Save the user's chat message as state["source_report"]."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        parts = ctx.user_content.parts if ctx.user_content else None
        source_report = "".join(p.text for p in parts or [] if p.text).strip()

        if not source_report:
            yield _message(
                ctx,
                self.name,
                f"[DEMO PLACEHOLDER: {self.name}] The chat message has no "
                "text, so source_report was not written.",
            )
            return

        yield _message(
            ctx,
            self.name,
            f"[DEMO PLACEHOLDER: {self.name}] Read the chat message. "
            f"Wrote source_report ({len(source_report)} characters).",
            {"source_report": source_report},
        )


class PlaceholderStage(BaseAgent):
    """Write fixed outputs to state so the pipeline runs without calling Gemini."""

    reads: list[str] = []
    outputs: dict[str, Any] = {}
    reply_key: Optional[str] = None  # an output to show as the chat reply

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        label = f"[DEMO PLACEHOLDER: {self.name}]"
        missing = [key for key in self.reads if key not in ctx.session.state]

        if missing:
            yield _message(
                ctx,
                self.name,
                f"{label} Missing state field(s): {', '.join(missing)}. "
                "Nothing was written.",
            )
            return

        text = (
            f"{label} Read {', '.join(self.reads)}. "
            f"Wrote {', '.join(self.outputs)}."
        )
        if self.reply_key:
            text += f"\n\n{self.outputs[self.reply_key]}"

        yield _message(ctx, self.name, text, dict(self.outputs))


# Fixed demo fixtures, based on baseline/examples/synthetic_chest_pain.json.
ATOMS = [
    {
        "text": "Serial troponin tests did not show a heart attack.",
        "type": "lab_value",
        "assertion": "negated",
        "source_quote": "Serial troponin tests did not show a heart attack.",
    },
    {
        "text": "Nuclear stress test result is pending.",
        "type": "procedure",
        "assertion": "pending",
        "source_quote": "its result is still pending",
    },
]

RETRIEVED_CONTEXT = (
    "Demo fixture paraphrasing MedlinePlus: Chest pain can have many causes, "
    "including heart problems, lung problems, and digestive problems such as "
    "acid reflux. (Source: https://medlineplus.gov/chestpain.html)"
)

DRAFT = (
    "You came to the hospital with chest pain. Blood tests did not show a "
    "heart attack. Your stress test result is not back yet. Your heart is "
    "healthy."
)

VERDICT = {
    "faithful": False,
    "unsupported_claims": ["Your heart is healthy."],
    "omissions": [],
    "reading_level_ok": True,
}

REVISED_DRAFT = (
    "You came to the hospital with chest pain. Blood tests did not show a "
    "heart attack. Your stress test result is not back yet."
)

FINAL_ANSWER = (
    "You came to the hospital because of chest pain. Blood tests showed you "
    "did not have a heart attack. We are still waiting for your stress test "
    "result."
)


root_agent = SequentialAgent(
    name="FaithfulMed",
    sub_agents=[
        Intake(name="Intake"),
        PlaceholderStage(
            name="Extractor",
            reads=["source_report"],
            outputs={"atoms": ATOMS},
        ),
        PlaceholderStage(
            name="Simplifier",
            reads=["atoms"],
            outputs={"retrieved_context": RETRIEVED_CONTEXT, "draft": DRAFT},
        ),
        PlaceholderStage(
            name="Verifier",
            reads=["source_report", "atoms", "draft"],
            outputs={"verdict": VERDICT},
        ),
        PlaceholderStage(
            name="Refiner",
            reads=["draft", "verdict"],
            outputs={"revised_draft": REVISED_DRAFT},
        ),
        PlaceholderStage(
            name="Readability",
            reads=["revised_draft"],
            outputs={"final_answer": FINAL_ANSWER},
            reply_key="final_answer",
        ),
    ],
)
