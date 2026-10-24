"""Carlin's ordered ADK scaffold with live roles and explicit offline modes."""

import asyncio
import json

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.genai import types

from .config import MODEL
from . import fixtures
from .roles.extractor import ClinicalAtoms, create_extractor, validate_source_quotes
from .roles.simplifier import run_simplifier
from .roles.verifier import verify
from .refiner_adapter import apply_verified_edits
from .roles.readability import run_readability


def emit(ctx, author, message, **updates):
    return Event(invocation_id=ctx.invocation_id, author=author,
                 content=types.Content(role='model', parts=[types.Part(text=message)]),
                 actions=EventActions(state_delta=updates))


def prepare(callback_context):
    message = ''.join(part.text or '' for part in callback_context.user_content.parts).strip()
    offline = message in ('/offline', '/offline-error')
    known = offline or message == '/demo'
    if message.startswith('/') and not known:
        return types.Content(parts=[types.Part(text='Use /demo, /offline, /offline-error, or paste a synthetic note.')])
    if not message:
        return types.Content(parts=[types.Part(text='Enter /demo or paste a synthetic note.')])
    # Reset all per-note state on EVERY turn; never reuse a previous patient's data.
    for key, value in dict(source_report=fixtures.SOURCE if known else message,
            atoms=[], retrieved_context=[], draft='', verdict={}, revised_draft='',
            final_answer='', final_verdict={}, readability_score={},
            readability_status='', suggestion=None, refinement_history=[],
            repair_blocker='', error='', run_status='running',
            mode='offline-scripted' if offline else 'live', model=MODEL,
            inject_demo_error=message == '/offline-error',
            retrieval_query=fixtures.EXAMPLE['retrieval_query'] if known else message[:1500],
            stage_modes={}).items():
        callback_context.state[key] = value


class DemoStage(BaseAgent):
    async def _run_async_impl(self, ctx):
        if ctx.session.state.get('run_status') == 'failed':
            return
        try:
            async for event in self.run_stage(ctx):
                yield event
        except Exception as exc:
            # Never send raw service exceptions (which can contain request details/keys) to the UI.
            code = getattr(exc, 'code', None)
            suffix = f' (service code {code})' if isinstance(code, int) else ''
            message = (f'{self.name} stopped: {type(exc).__name__}{suffix}. '
                       'Check the API key/quota, model access, and Gemini index setup. '
                       'No final answer was produced. Use /offline for the scripted walkthrough.')
            yield emit(ctx, self.name, message, run_status='failed', error=message, final_answer='')


class IntakeStage(DemoStage):
    """Carlin's intake step, with the prepared demo command resolved first."""

    async def run_stage(self, ctx):
        source = ctx.session.state['source_report']
        if not source.strip():
            raise ValueError('The source report is empty.')
        yield emit(ctx, self.name, f'Intake saved the source note ({len(source)} characters).')


class ExtractorStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        offline = state['mode'] == 'offline-scripted'
        mode = 'scripted atoms for fixed example' if offline else 'live Gemini / Vaibhavi Extractor'
        yield emit(ctx, self.name, f'Extractor — {mode}\n\nSource note:\n{state["source_report"]}',
                   stage_modes={'Extractor': mode})
        if offline:
            atoms = ClinicalAtoms.model_validate(fixtures.ATOMS)
        else:
            async for event in self.sub_agents[0].run_async(ctx):
                if event.error_code:
                    raise ValueError('Extractor model error.')
                yield event
            raw = state['atoms']
            atoms = ClinicalAtoms.model_validate_json(raw) if isinstance(raw, str) else ClinicalAtoms.model_validate(raw)
        if not atoms.root:
            raise ValueError('No clinical facts extracted.')
        yield emit(ctx, self.name, 'Source-linked atoms:\n' + atoms.model_dump_json(indent=2),
                   atoms=atoms.model_dump())


class QuoteCheckStage(DemoStage):
    """Carlin's quote check; a failed quote now stops later stages."""

    async def run_stage(self, ctx):
        state = ctx.session.state
        atoms = ClinicalAtoms.model_validate(state['atoms'])
        validate_source_quotes(state['source_report'], atoms.root)
        yield emit(ctx, self.name, f'All {len(atoms.root)} source quotes found in the note.')


class SimplifierStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        if state['mode'] == 'offline-scripted':
            context = fixtures.CONTEXT
            draft = fixtures.DRAFT + (' ' + fixtures.BAD_CLAIM if state['inject_demo_error'] else '')
            mode = 'scripted draft and cited fixture; no model call or vector search'
        else:
            from retrieval.gemini_chroma import search
            context = await asyncio.to_thread(search, state['retrieval_query'])
            if not context or not any(row['text'].strip() for row in context):
                raise ValueError('No usable retrieval context.')
            mode = 'live Gemini draft with Gemini/Chroma retrieval'
            yield emit(ctx, self.name, 'Retrieved MedlinePlus passages:\n' + json.dumps(context, indent=2),
                       retrieved_context=context)
            draft = await asyncio.to_thread(run_simplifier, state['atoms'], json.dumps(context),
                                            model=state['model'], source_report=state['source_report'])
        yield emit(ctx, self.name, f'Simplifier — {mode}\n\n{draft}\n\nContext:\n' + json.dumps(context, indent=2),
                   draft=draft, retrieved_context=context,
                   stage_modes={**state['stage_modes'], 'Simplifier': mode})


async def judge(state, text):
    if state['mode'] == 'offline-scripted':
        return fixtures.fixture_verdict(text)
    return await asyncio.to_thread(verify, state['source_report'], state['atoms'], text,
                                   state['retrieved_context'], model=state['model'])


class VerifierStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        verdict = await judge(state, state['draft'])
        mode = 'scripted fixture check' if state['mode'] == 'offline-scripted' else 'live Gemini judgment; uncalibrated'
        yield emit(ctx, self.name, f'Verifier — {mode}\n\n' + json.dumps(verdict, indent=2),
                   verdict=verdict, stage_modes={**state['stage_modes'], 'Verifier': mode})


class RefinerStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        text, verdict, history, blocker = state['draft'], state['verdict'], [], ''
        # At most two targeted repair rounds. Every changed draft is rechecked.
        for round_number in range(1, 3):
            if not verdict['issues']:
                break
            try:
                text = apply_verified_edits(text, verdict, state['source_report'])
            except ValueError as exc:
                blocker = str(exc)
                break
            verdict = await judge(state, text)
            history.append({'round': round_number, 'revised_draft': text, 'verdict': verdict})
            yield emit(ctx, self.name, f'Repair {round_number}; recheck:\n' + json.dumps(verdict, indent=2),
                       refinement_history=history)
        mode = 'Zurabi exact-source edits; max two rounds; recheck after edits'
        label = ('Repair needs review: ' + blocker if blocker else
                 'No edits needed.' if not history else 'Targeted repairs completed.')
        yield emit(ctx, self.name, label + '\n\n' + text,
                   revised_draft=text, final_verdict=verdict, repair_blocker=blocker,
                   stage_modes={**state['stage_modes'], 'Refiner': mode})


class ReadabilityStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        result = await asyncio.to_thread(run_readability, state['revised_draft'])
        unresolved = bool(state['final_verdict']['issues']) or bool(state['repair_blocker'])
        status = 'needs_review' if unresolved else ('complete' if result['readability_pass'] else result['readability_status'])
        # The initial demo reports readability failures; it does not rewrite again.
        banner = 'OFFLINE SCRIPTED WALKTHROUGH' if state['mode'] == 'offline-scripted' else 'LIVE DEMO — uncalibrated'
        grade = result['readability_score']['flesch_kincaid_grade']
        passed = result['readability_pass']
        answer = result['final_answer'] if not unresolved else None
        display_answer = answer or 'Draft for review:\n' + state['revised_draft']
        message = (f'{banner}\n\n{display_answer}\n\n'
                   f'Readability: grade {grade}; grade-8 check passed: {passed}. '
                   'Scorer status "ok" means it measured the text; '
                   f'readability status "{result["readability_status"]}" is Alicia’s pass decision.\n'
                   f'{result["suggestion"] or ""}\n'
                   + ('Unresolved Verifier findings: needs review.' if unresolved else
                      'No unresolved findings in this demo check. This is not a clinical validation.'))
        updates = {'final_answer': answer or '',
                   'readability_status': result['readability_status'],
                   'readability_score': result['readability_score'],
                   'suggestion': result['suggestion'],
                   'run_status': status,
                   'stage_modes': {**state['stage_modes'], 'Readability': 'Alicia wrapper; no rewrite'}}
        yield emit(ctx, self.name, message, **updates)


def build_agent():
    extractor = create_extractor(MODEL)
    extractor.name = 'ClinicalExtractor'
    extractor.include_contents = 'none'
    return SequentialAgent(name='FaithfulMed', description='Seven-stage clinical explanation demo. Start with /offline-error or /demo.',
        before_agent_callback=prepare,
        sub_agents=[IntakeStage(name='Intake'),
                    ExtractorStage(name='Extractor', sub_agents=[extractor]),
                    QuoteCheckStage(name='QuoteCheck'),
                    SimplifierStage(name='Simplifier'), VerifierStage(name='Verifier'),
                    RefinerStage(name='Refiner'), ReadabilityStage(name='Readability')])


root_agent = build_agent()
