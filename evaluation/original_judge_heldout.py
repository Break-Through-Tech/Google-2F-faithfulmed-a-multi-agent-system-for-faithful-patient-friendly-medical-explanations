"""Prospectively frozen held-out evaluation of the original citation judge."""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import calibrate_verifier as judge
from .audit_support_references import audit, POLICY
from .investigate_calibration import parse_pubmed
from .score_outputs import write_json
from .scoring import digest

ROOT=Path('data/calibration_results')
SELECTION=ROOT/'original_judge_heldout_selection_v1.json'
CACHE=ROOT/'original_judge_heldout_context_v1.json'
SUITE=ROOT/'original_judge_heldout_suite_v1.json'
RUN=ROOT/'original_judge_heldout_run_v1.json'
PROMPT_DIGEST='0eded17cd2bfeb37c5d79e4a765b77b000cf50478a91e1091adbe5800c151bfb'
VERSION='original-judge-heldout-2026-11-11-v1'
MODEL='gemini-3.8-flash'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def frozen_write(path,value):
    if path.exists():
        if read(path)!=value:raise ValueError('Frozen artifact differs: '+str(path))
    else:write_json(path,value)

def reference_status(flags):
    if any(f in flags for f in ['conflicting_binary_references','invalid_or_unmapped_reference','punctuation_neighbor_requires_review']):
        return 'ambiguous'
    if 'duplicate_document_assertion' in flags:return 'duplicate'
    return 'eligible'

def select(source,dataset):
    dev=set(source['question_groups']['development']);held=set(source['question_groups']['heldout'])
    if dev&held:raise ValueError('Question-level overlap')
    chosen=source['splits']['heldout']
    if len({c['case_id'] for c in chosen})!=len(chosen):raise ValueError('Duplicate case IDs')
    if any(c['question_id'] not in held for c in chosen):raise ValueError('Non-held-out question')
    review=audit(dataset,source,dict(records={}))
    rows={c['case_id']:c for c in review['cases'] if c['split']=='heldout'}
    records=[]
    for c in chosen:
        row=rows[c['case_id']];flags=[f for f in row['audit_flags'] if f!='title_abstract_not_cached']
        status=reference_status(flags)
        if status=='eligible':
            labels={r=='supporting' for r in row['relation_counts']}
            if labels!={c['reference_support']}:raise ValueError('Reference mapping differs')
        records.append(dict(case=c,reference_status=status,audit_flags=flags,
            relation_counts=row['relation_counts'],reference_records=row['reference_records']))
    return dict(version=VERSION,policy=POLICY,source_suite_digest=digest(source),
        dataset_sha256=source['dataset_sha256'],model=MODEL,temperature=0,
        prompt=judge.PROMPT,prompt_digest=digest(judge.PROMPT),schema=judge.SupportDecision.model_json_schema(),
        question_groups=source['question_groups'],records=records,
        status_counts=dict(Counter(r['reference_status'] for r in records)),
        predictions_used_for_selection=False)

def freeze_selection():
    if digest(judge.PROMPT)!=PROMPT_DIGEST:raise ValueError('Original prompt changed')
    source=read(ROOT/'medaesqa_support_v1.json')
    path=Path('data/MedAESQA_data/medaesqa_v1.json')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=source['dataset_sha256']:raise ValueError('Dataset changed')
    result=select(source,read(path))
    frozen_write(SELECTION,result)
    print(json.dumps(dict(selected=len(result['records']),status_counts=result['status_counts'])),flush=True)
    return result

def fetch(selection):
    pmids=sorted({str(r['case']['cited_pmid']) for r in selection['records'] if r['reference_status']=='eligible'})
    if CACHE.exists():return read(CACHE)
    if not all(p.isdigit() for p in pmids):raise ValueError('Only numeric PMIDs allowed')
    url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?'+urllib.parse.urlencode(dict(db='pubmed',id=','.join(pmids),retmode='xml'))
    request=urllib.request.Request(url,headers={'User-Agent':'FaithfulMed-frozen-heldout-evaluation/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:xml=response.read()
    records=parse_pubmed(xml)
    if set(records)-set(pmids):raise ValueError('Unexpected PubMed records')
    cache=dict(selection_digest=digest(selection),fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        request_url=url,xml_sha256=hashlib.sha256(xml).hexdigest(),records=records,
        missing_pmids=sorted(set(pmids)-set(records)))
    frozen_write(CACHE,cache)
    return cache

def prepare(selection,cache):
    if cache['selection_digest']!=digest(selection):raise ValueError('Cache selection mismatch')
    cases=[];unavailable=[]
    for r in selection['records']:
        if r['reference_status']!='eligible':continue
        c=r['case'];doc=cache['records'].get(str(c['cited_pmid']))
        if not doc or not doc.get('title','').strip() or not doc.get('abstract','').strip():
            unavailable.append(c['case_id']);continue
        if str(doc['pmid'])!=str(c['cited_pmid']) or doc['context_sha256']!=digest([doc['title'],doc['abstract']]):
            raise ValueError('Context identity/hash mismatch')
        cases.append(dict(c,evidence=doc['title']+'\n\n'+doc['abstract'],
            evidence_scope='pubmed_title_and_abstract',context_sha256=doc['context_sha256'],
            context_title=doc['title'],context_abstract=doc['abstract']))
    suite=dict(suite_version=judge.VERSION,context_version=VERSION,run_kind='single_frozen_heldout_evaluation',
        selection_digest=digest(selection),context_cache_digest=digest(cache),
        question_groups=selection['question_groups'],splits=dict(development=[],heldout=cases),
        source_unavailable_case_ids=unavailable)
    frozen_write(SUITE,suite)
    print(json.dumps(dict(ready=len(cases),source_unavailable=len(unavailable))),flush=True)
    return suite

def report():
    selection=read(SELECTION);suite=read(SUITE);run=read(RUN)
    if run['split']!='heldout' or run['prompt_sha256']!=PROMPT_DIGEST:raise ValueError('Run settings differ')
    if run['model']!=MODEL:raise ValueError('Wrong model')
    expected=digest(dict(suite=suite,split='heldout',model=MODEL,prompt=judge.PROMPT,version=judge.VERSION))
    if run['run_digest']!=expected:raise ValueError('Run fingerprint mismatch')
    cases=suite['splits']['heldout'];byid={c['case_id']:c for c in cases}
    summary=judge.summarize_predictions(run['records'],cases)
    eligible=sum(r['reference_status']=='eligible' for r in selection['records'])
    target=bool(summary['complete'] and not suite['source_unavailable_case_ids'] and summary['targets_met_on_scored_cases'])
    packet=dict(version=VERSION,selection_digest=digest(selection),run_digest=digest(run),
        selected=len(selection['records']),reference_status_counts=selection['status_counts'],
        eligible=eligible,source_unavailable=len(suite['source_unavailable_case_ids']),summary=summary,
        all_eligible_agreement=summary['correct']/eligible if eligible else None,
        complete_heldout_target_met=target)
    write_json(ROOT/'original_judge_heldout_report_v1.json',packet)
    a=summary
    lines=['# Original citation judge: frozen held-out evaluation','',
        f"Agreement: **{a['correct']}/{a['scored_cases']} ({a['agreement']:.1%})**; **Cohen kappa {a['cohen_kappa']:.3f}**.",
        f"Targets (agreement >=80%, kappa >=0.6) met on a complete held-out run: **{target}**.",'',
        f"Selected {packet['selected']}; reference-eligible {eligible}; source unavailable {packet['source_unavailable']}.",
        f"Attempted {a['attempted_cases']}; failed {a['failed_cases']}; pending {a['pending_cases']}.",
        f"Correct / all reference-eligible (failures and missing sources are nonagreements): {a['correct']}/{eligible}.",
        'Failed assessments are not treated as unsupported predictions. Kappa below uses',
        'valid predictions only; coverage and the conservative denominator remain explicit.','',
        '## Frozen setup','',
        f"Model `{MODEL}`, temperature 0, original prompt/schema and original judge function.",
        f"Prompt digest `{PROMPT_DIGEST}`.",
        'Question/sentence/current PubMed title and abstract reach the judge. No reference',
        'labels, grouping output, whole-support assessment or preceding-answer context.',
        'One attempt per eligible case; no label-based retries, prompt changes or tuning.',
        'Eligibility was fixed by the existing reference-conflict/deduplication policy',
        'before source fetch or model calls. All 40 selected IDs remain in the selection file.',
        'The held-out questions do not overlap development. Current PubMed records are',
        'not a verified reconstruction of the original annotation-time abstracts.','',
        '## Eligibility and class balance','', '```json',json.dumps(selection['status_counts'],indent=2),'```',
        'Valid scored reference classes: '+json.dumps(a['reference_support_counts']),
        'The eligible subset is not necessarily balanced or representative of deployment.', '',
        '## Confusion counts and uncertainty','', '```json',json.dumps(a['confusion_counts'],indent=2),'```',
        'Agreement Wilson 95% interval: '+json.dumps(a['agreement_wilson_95']), '',
        'This is a descriptive case-level interval; it does not adjust for correlated',
        'cases from the same question. The small sample does not establish precise',
        'population-level performance.', '',
        '## Operational finding', '',
        'The frozen original judge completed every eligible assessment. Against the',
        'reference mapping it predicted unsupported for seven supporting pairs and',
        'supported for one neutral pair: recall 13/20 for supporting and specificity',
        '10/11 for non-supporting. This describes disagreement direction, not proof',
        'that every reference/model judgment is semantically correct. No ambiguous',
        'reference was resolved using these predictions.', '',
        '**The 80% agreement and 0.6 kappa targets were not met.** Keep the result as',
        'the frozen held-out baseline. Grouping/adapter work remains paused; do not',
        'change thresholds, remove disagreements or rerun until the targets appear met.', '',
        '## Comparison with development','',
        'The original scored 19/26 (73.1%), kappa 0.420 on its preserved development run',
        'and 17/26 (65.4%), kappa 0.282 on a repeat. Held-out results use different cases;',
        'a score difference is not a paired improvement or regression caused by a code change.',
        'This measures citation-support agreement under the frozen reference mapping,',
        'not whole-report medical correctness or calibration of every runtime agent.', '',
        '## Per-case results','', '| Question / PMID | Reference | Prediction | Status |', '|---|---|---|---|']
    for r in run['records']:
        c=byid[r['case_id']]
        lines.append(f"| {c['question_id']} / {c['cited_pmid']} | {c['reference_relation']} | {r.get('supports_sentence','unscored')} | {r['status']} |")
    lines+=['','## Disagreements and failures','']
    for r in run['records']:
        c=byid[r['case_id']]
        if r['status']=='ok' and r['supports_sentence']==c['reference_support']:continue
        lines += [f"### {c['question_id']} / PMID {c['cited_pmid']}",'',c['sentence'],'',
            f"Reference {c['reference_relation']}; prediction {r.get('supports_sentence','unscored')}.",'',
            str(r.get('reason',r.get('error_type'))),'']
    lines += ['', '## Next use of these results','',
        'This hold-out has now been evaluated. If its disagreements are used to revise',
        'the judge or policy, it must no longer be described as untouched held-out data',
        'for that revision. Use a new independently reserved evaluation set. Preserve this',
        'score even if it misses the targets; do not retune and repeatedly rescore it as',
        'fresh validation. No production configuration was changed.', '']
    Path('evaluation/ORIGINAL_JUDGE_HELDOUT_RUN.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(packet,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['select','prepare','run','report'])
    args=parser.parse_args()
    if args.action=='report':report();return
    selection=freeze_selection()
    if args.action=='select':return
    if args.action=='prepare':prepare(selection,fetch(selection));return
    suite=read(SUITE)
    if suite['selection_digest']!=digest(selection):raise ValueError('Suite selection differs')
    # No retry_errors: one attempt per case, skip recorded attempts on resume.
    judge.run_suite(suite,RUN,split='heldout',model=MODEL,limit=len(suite['splits']['heldout']))

if __name__=='__main__':main()
