"""FaithfulMed ADK entry point for `adk web .` (skeleton only)."""

import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.agents import BaseAgent, InvocationContext, SequentialAgent
from google.adk.events import Event
from google.genai import types

# Load the key without printing it. A missing .env or key is fine here.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

PLACEHOLDER_TEXT = (
    "[DEMO PLACEHOLDER] FaithfulMed pipeline skeleton. "
    "No model was called; the five stages are not wired up yet."
)


class PlaceholderStage(BaseAgent):
    """Reply with fixed text so the pipeline runs without calling Gemini."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=PLACEHOLDER_TEXT)],
            ),
        )


root_agent = SequentialAgent(
    name="FaithfulMed",
    sub_agents=[PlaceholderStage(name="Placeholder")],
)
