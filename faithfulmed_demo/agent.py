"""Carlin's ordered ADK scaffold with live roles and explicit offline modes."""

import asyncio
import json

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.genai import types

from .config import MODEL
from . import execution_trace as execution
from . import fixtures
from .roles.extractor import ClinicalAtoms, create_extractor, validate_source_quotes
from .roles.simplifier import run_simplifier
from .roles.verifier import verify
from .refiner_adapter import apply_verified_edits
from .roles.readability import run_readability, rewrite_for_readability, MAX_REWRITES


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
            readability_history=[], faithfulness_recheck_required=False,
            repair_blocker='', error='', run_status='running',
            mode='offline-scripted' if offline else 'live', model=MODEL,
            inject_demo_error=message == '/offline-error',
            retrieval_query=fixtures.EXAMPLE['retrieval_query'] if known else message,
            stage_modes={}, execution_trace=[]).items():
        callback_context.state[key] = value


class DemoStage(BaseAgent):
    async def _run_async_impl(self, ctx):
        if ctx.session.state.get('run_status') == 'failed':
            yield execution.skip(ctx,self.name,self.name,'stage','An earlier stage failed')
            return
        token=execution.start(ctx,self.name,self.name,'stage')
        yield execution.event(ctx)
        try:
            async for event in self.run_stage(ctx):
                yield event
        except Exception as exc:
            execution.fail_open_calls(ctx,self.name,exc)
            yield execution.finish(ctx,token,'failed',error=exc)
            # Never send raw service exceptions (which can contain request details/keys) to the UI.
            code = getattr(exc, 'code', None)
            suffix = f' (service code {code})' if isinstance(code, int) else ''
            message = (f'{self.name} stopped: {type(exc).__name__}{suffix}. '
                       'Check the API key/quota, model access, and Gemini index setup. '
                       'No final answer was produced. Use /offline for the scripted walkthrough.')
            yield emit(ctx, self.name, message, run_status='failed', error=message, final_answer='')
        else:
            yield execution.finish(ctx,token)


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
            yield execution.skip(ctx,self.name,'ClinicalExtractor / Gemini','model','Scripted facts; no model call')
        else:
            token=execution.start(ctx,self.name,'ClinicalExtractor / Gemini','model',{'report':state['source_report'],'model':state['model']})
            yield execution.event(ctx)
            async for event in self.sub_agents[0].run_async(ctx):
                if event.error_code:
                    raise ValueError('Extractor model error.')
                yield event
            raw = state['atoms']
            atoms = ClinicalAtoms.model_validate_json(raw) if isinstance(raw, str) else ClinicalAtoms.model_validate(raw)
            yield execution.finish(ctx,token,output=atoms.model_dump())
        if not atoms.root:
            raise ValueError('No clinical facts extracted.')
        yield emit(ctx, self.name, 'Source-linked atoms:\n' + atoms.model_dump_json(indent=2),
                   atoms=atoms.model_dump())


class QuoteCheckStage(DemoStage):
    """Carlin's quote check; a failed quote now stops later stages."""

    async def run_stage(self, ctx):
        state = ctx.session.state
        atoms = ClinicalAtoms.model_validate(state['atoms'])
        box={}
        async for e in execution.call(ctx,self.name,'validate_source_quotes','local',validate_source_quotes,box,
                state['source_report'],atoms.root,inputs={'fact_count':len(atoms.root)}):yield e
        yield emit(ctx, self.name, f'All {len(atoms.root)} source quotes found in the note.')


class SimplifierStage(DemoStage):
    async def run_stage(self, ctx):
        state = ctx.session.state
        if state['mode'] == 'offline-scripted':
            context = fixtures.CONTEXT
            draft = fixtures.DRAFT + (' ' + fixtures.BAD_CLAIM if state['inject_demo_error'] else '')
            mode = 'scripted draft and cited fixture; no model call or vector search'
            yield execution.skip(ctx,self.name,'MedlinePlus search','retrieval','Scripted reference passage')
            yield execution.skip(ctx,self.name,'run_simplifier / Gemini','model','Scripted draft')
        else:
            from retrieval.gemini_chroma import search
            box={}
            async for e in execution.call(ctx,self.name,'gemini_chroma.search','retrieval',search,box,
                    state['retrieval_query'],inputs={'query':state['retrieval_query']}):yield e
            context=box['result']
            if not context or not any(row['text'].strip() for row in context):
                raise ValueError('No usable retrieval context.')
            mode = 'live Gemini draft with Gemini/Chroma retrieval'
            yield emit(ctx, self.name, 'Retrieved MedlinePlus passages:\n' + json.dumps(context, indent=2),
                       retrieved_context=context)
            async for e in execution.call(ctx,self.name,'run_simplifier / Gemini','model',run_simplifier,box,
                    state['atoms'],json.dumps(context),model=state['model'],source_report=state['source_report'],
                    inputs={'fact_count':len(state['atoms']),'passage_count':len(context),'model':state['model']}):yield e
            draft=box['result']
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
        box={}
        async for e in execution.call(ctx,self.name,'Verifier judgment','scripted' if state['mode']=='offline-scripted' else 'model',
                judge,box,state,state['draft'],inputs={'draft':state['draft']}):yield e
        verdict=box['result']
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
                if not history:yield execution.skip(ctx,self.name,'apply_verified_edits','local','No verifier findings; no edits needed')
                break
            try:
                box={}
                async for e in execution.call(ctx,self.name,f'apply_verified_edits / round {round_number}','local',
                        apply_verified_edits,box,text,verdict,state['source_report'],inputs={'draft':text,'findings':verdict['issues']}):yield e
                text=box['result']
            except ValueError as exc:
                blocker = str(exc)
                break
            async for e in execution.call(ctx,self.name,f'Verifier recheck / repair {round_number}',
                    'scripted' if state['mode']=='offline-scripted' else 'model',judge,box,state,text,inputs={'draft':text}):yield e
            verdict=box['result']
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
        text, verdict = state['revised_draft'], state['final_verdict']
        box={}
        async for e in execution.call(ctx,self.name,'run_readability','local',run_readability,box,text,inputs={'text':text}):yield e
        result=box['result']
        unresolved = bool(state['final_verdict']['issues']) or bool(state['repair_blocker'])
        history, blocker = [], state['repair_blocker']
        # Readability rewrites are separate from Zurabi's exact clinical repairs.
        # Never use wording changes to bypass unresolved clinical findings.
        if state['mode'] != 'offline-scripted' and not unresolved:
            for round_number in range(1, MAX_REWRITES + 1):
                if result['readability_status'] != 'needs_simplification':
                    break
                async for e in execution.call(ctx,self.name,f'Readability rewrite / round {round_number}','model',rewrite_for_readability,box,text,
                    state['source_report'], state['atoms'], state['retrieved_context'],
                    model=state['model'], current_score=result['readability_score'],inputs={'draft':text,'score':result['readability_score']}):yield e
                candidate=box['result']
                if not isinstance(candidate, str) or not candidate.strip():
                    raise ValueError('Readability rewrite returned empty text.')
                entry = {'round': round_number, 'input_draft': text,
                         'before_score': result['readability_score'], 'candidate': candidate,
                         'verdict': None, 'after_score': None, 'accepted': False}
                history.append(entry)
                yield emit(ctx, self.name,
                    f'Readability rewrite {round_number}: checking faithfulness before release.',
                    readability_history=history, faithfulness_recheck_required=True, final_answer='')
                async for e in execution.call(ctx,self.name,f'Verifier recheck / wording {round_number}','model',judge,box,state,candidate,
                        inputs={'candidate':candidate}):yield e
                candidate_verdict=box['result']
                async for e in execution.call(ctx,self.name,f'run_readability / round {round_number}','local',run_readability,box,candidate,
                        inputs={'text':candidate}):yield e
                candidate_result=box['result']
                entry.update(verdict=candidate_verdict, after_score=candidate_result['readability_score'])
                if candidate_verdict['issues']:
                    blocker = 'Readability rewrite introduced or exposed Verifier findings; review required.'
                    unresolved = True
                    yield emit(ctx, self.name, blocker + '\n' + json.dumps(candidate_verdict, indent=2),
                               readability_history=history, faithfulness_recheck_required=False)
                    break
                if (candidate_result['readability_status'] in ('invalid', 'needs_review')
                        or candidate_result['readability_score'].get('flesch_kincaid_grade', float('inf'))
                        >= result['readability_score']['flesch_kincaid_grade']):
                    entry['stop_reason'] = 'Rewrite did not improve readability; retained the verified draft.'
                    yield emit(ctx, self.name, entry['stop_reason'], readability_history=history,
                               faithfulness_recheck_required=False)
                    break
                entry['accepted'] = True
                text, verdict, result = candidate, candidate_verdict, candidate_result
                yield emit(ctx, self.name, f'Readability rewrite {round_number} passed the Verifier recheck.',
                           revised_draft=text, final_verdict=verdict, readability_history=history,
                           faithfulness_recheck_required=False)
        if not history:
            reason=('Scripted walkthrough; no rewrite' if state['mode']=='offline-scripted' else
                    'Unresolved clinical findings' if unresolved else 'No rewrite required by readability check')
            yield execution.skip(ctx,self.name,'Readability rewrite','model',reason)
        status = 'needs_review' if unresolved else ('complete' if result['readability_pass'] else result['readability_status'])
        banner = 'OFFLINE SCRIPTED WALKTHROUGH' if state['mode'] == 'offline-scripted' else 'LIVE DEMO — uncalibrated'
        grade = result['readability_score'].get('flesch_kincaid_grade')
        passed = result['readability_pass']
        answer = result['final_answer'] if not unresolved else None
        display_answer = answer or 'Draft for review:\n' + text
        message = (f'{banner}\n\n{display_answer}\n\n'
                   f'Readability: grade {grade}; grade-8 check passed: {passed}. '
                   'Scorer status "ok" means it measured the text; '
                   f'readability status "{result["readability_status"]}" is Alicia’s pass decision.\n'
                   f'{result["suggestion"] or ""}\n'
                   + ('Unresolved Verifier findings: needs review.' if unresolved else
                      'No unresolved findings in this demo check. This is not a clinical validation.'))
        updates = {'final_answer': answer or '',
                   'revised_draft': text, 'final_verdict': verdict,
                   'repair_blocker': blocker, 'readability_history': history,
                   'faithfulness_recheck_required': False,
                   'readability_status': result['readability_status'],
                   'readability_score': result['readability_score'],
                   'suggestion': result['suggestion'],
                   'run_status': status,
                   'stage_modes': {**state['stage_modes'], 'Readability':
                       'Alicia scorer; at most two live wording rewrites, each reverified'
                       if state['mode'] != 'offline-scripted' else 'Alicia scorer; scripted walkthrough; no rewrite'}}
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
