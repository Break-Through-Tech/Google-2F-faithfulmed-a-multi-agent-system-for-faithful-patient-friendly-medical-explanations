"""Run an isolated ADK session and expose its saved state to the UI."""

import asyncio
import copy
from dataclasses import dataclass, field
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from faithfulmed_demo import fixtures
from faithfulmed_demo.agent import build_agent

STAGES = ("Intake", "Extractor", "QuoteCheck", "Simplifier", "Verifier", "Refiner", "Readability")
LIVE = "Live Gemini"
OFFLINE = "Scripted walkthrough"
REPAIR = "Scripted repair walkthrough"
MODES = (LIVE, OFFLINE, REPAIR)
MAX_CHARACTERS = 30000


@dataclass
class Snapshot:
    state: dict = field(default_factory=dict)
    completed: list[str] = field(default_factory=list)
    active: str = "Intake"
    finished: bool = False
    error: str = ""


def request_message(report: str, mode: str) -> str:
    if mode not in MODES:
        raise ValueError("Choose a supported run mode.")
    if mode != LIVE:
        return "/offline-error" if mode == REPAIR else "/offline"
    if not isinstance(report, str) or not report.strip():
        raise ValueError("Paste a report or choose an example before running.")
    if len(report) > MAX_CHARACTERS:
        raise ValueError("Use a report of 30,000 characters or fewer for this demo.")
    if report.lstrip().startswith("/"):
        raise ValueError("Paste the medical report itself. Choose walkthroughs using the run mode selector.")
    # Preserve /demo's focused query for the unchanged built-in example only.
    return "/demo" if report.strip() == fixtures.SOURCE.strip() else report


def completed_stage(author: str, delta: dict) -> str | None:
    if delta.get("run_status") == "failed":
        return None
    if author == "Intake":
        return "Intake"
    if author == "Extractor" and isinstance(delta.get("atoms"), list):
        return "Extractor"
    if author == "QuoteCheck":
        return "QuoteCheck"
    for stage, key in (("Simplifier", "draft"), ("Verifier", "verdict"),
                       ("Refiner", "revised_draft"), ("Readability", "readability_score")):
        if author == stage and key in delta:
            return stage
    return None


async def stream_run(report: str, mode: str, *, timeout: float = 600):
    """Every request gets its own runner, agent, and memory-only session."""
    view = Snapshot()
    try:
        message = request_message(report, mode)
    except ValueError as exc:
        view.error, view.finished = str(exc), True
        yield view
        return

    view.state = {"source_report": fixtures.SOURCE if message.startswith("/") else report.strip(),
                  "mode": "live" if mode == LIVE else "offline-scripted", "run_status": "running"}
    yield copy.deepcopy(view)
    sessions = InMemorySessionService()
    identity = uuid4().hex
    runner = None
    try:
        async with asyncio.timeout(timeout):
            await sessions.create_session(app_name="faithfulmed_ui", user_id=identity, session_id=identity)
            runner = Runner(agent=build_agent(), app_name="faithfulmed_ui", session_service=sessions)
            async for event in runner.run_async(user_id=identity, session_id=identity,
                    new_message=types.Content(role="user", parts=[types.Part(text=message)])):
                delta = dict(event.actions.state_delta or {}) if event.actions else {}
                view.state.update(copy.deepcopy(delta))
                author = "Extractor" if event.author == "ClinicalExtractor" else event.author
                if author in STAGES:
                    view.active = author
                done = completed_stage(event.author, delta)
                if done and done not in view.completed:
                    view.completed.append(done)
                    index = STAGES.index(done)
                    if index + 1 < len(STAGES):
                        view.active = STAGES[index + 1]
                if view.state.get("run_status") == "failed":
                    view.error = view.state.get("error") or "The pipeline stopped before producing a final answer."
                yield copy.deepcopy(view)
            session = await sessions.get_session(app_name="faithfulmed_ui", user_id=identity, session_id=identity)
            if session:
                view.state = copy.deepcopy(session.state)
            if view.state.get("run_status") == "running":
                view.error = "The pipeline ended before all stages finished. Try a new run."
    except TimeoutError:
        view.error = "The run exceeded ten minutes. Check API availability and try again."
    except Exception as exc:
        # Service exception bodies can contain request data or credentials.
        code = getattr(exc, "code", None)
        suffix = f" (service code {code})" if isinstance(code, int) else ""
        view.error = f"The run stopped{suffix}. Check the local API/model configuration and try again."
    finally:
        await sessions.delete_session(app_name="faithfulmed_ui", user_id=identity, session_id=identity)
        if runner is not None:
            await runner.close()
    if view.error:
        view.state.update(run_status="failed", final_answer="")
    view.finished = True
    yield copy.deepcopy(view)
