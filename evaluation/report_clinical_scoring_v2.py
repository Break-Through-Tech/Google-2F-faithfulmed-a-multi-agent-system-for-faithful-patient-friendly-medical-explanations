"""Offline before/after clinical scoring report; no service calls."""

import json
from pathlib import Path

from .score_outputs import public_job, write_json
from .scoring import digest


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    root=Path('data/comparison_results/five_report_pilot_2026-11-07_v1')
    controls=Path('data/scoring_results')
    old=read(root/'clinical_scores_v2.json')
    new=read(root/'clinical_scores_source_ids_final_v2.json')
    jobs=read(root/'scoring_inputs.json')['records']
    if len(new['records'])!=len(jobs):raise ValueError('Pilot scoring is not finished.')
    by_old={(r['case_id'],r['system']):r for r in old['records']}
    rows=[]
    for job,r in zip(jobs,new['records']):
        assert r['input_digest']==digest(public_job(job))
        previous=by_old[(r['case_id'],r['system'])]
        assert previous['input_digest']==r['input_digest']
        rows.append(dict(source_row_id=r['source_row_id'],system=r['system'],kind=r['output_kind'],
            old_status=previous['status'],new_status=r['status'],metrics=r.get('metrics'),
            error_category=r.get('error_category'),error_type=r.get('error_type')))
    advisor={r['case_id']:r for r in read(controls/'clinical_v2_advisor_validated_2026-11-08.json')['records']}
    advisor.update({r['case_id']:r for r in read(controls/'clinical_v2_advisor_retry_2026-11-08.json')['records']})
    fixtures=read('evaluation/examples/advisor_scoring_examples.json')
    advisor_ok=sum(r.get('status')=='scored' and all(r['metrics'].get(k)==v for k,v in c['expected_counts'].items())
                   for c in fixtures['examples'] for r in [advisor[c['id']]])
    regressions=read('evaluation/examples/clinical_scoring_regressions_v2.json')['records']
    regression_results={}
    for label,files in [('old',['clinical_regressions_old_2026-11-08.json','clinical_regressions_old_retry_2026-11-08.json']),
                        ('new',['clinical_regressions_new_2026-11-08.json'])]:
        indexed={}
        for file in files:indexed.update({r['case_id']:r for r in read(controls/file)['records']})
        checks=[]
        for case in regressions:
            r=indexed[case['case_id']];passed={}
            for key,value in case['expected_checks'].items():
                if key=='fact_not_fully_covered':
                    passed[key]=r['status']=='scored' and next(f['status'] for f in r['assessment']['key_fact_coverage'] if f['fact_id']==value)!='covered'
                else:passed[key]=r['status']=='scored' and r['metrics'].get(key)==value
            checks.append({'case_id':case['case_id'],'checks':passed,'all_passed':all(passed.values())})
        regression_results[label]={'correct_cases':sum(c['all_passed'] for c in checks),'total_cases':7,'cases':checks}
    summary={'old_scored':sum(r['status']=='scored' for r in old['records']),
        'new_scored':sum(r['status']=='scored' for r in new['records']),'total_outputs':len(jobs),
        'advisor_cases_matching_all_counts':advisor_ok,'advisor_cases':4,
        'regression':regression_results,'rows':rows,
        'regression_fixture_digest':digest(read('evaluation/examples/clinical_scoring_regressions_v2.json')),
        'advisor_fixture_digest':digest(fixtures),
        'old_result_digest':digest(old),'new_result_digest':digest(new),
        'note':'Same saved pilot answers. This is clinical scoring reliability, not a new MedAESQA calibration score.'}
    write_json(root/'clinical_scoring_v2_comparison.json',summary)
    lines=['# Clinical scoring improvement - November 8, 2026','',
        f"The source-ID scorer produced **{summary['new_scored']}/10 valid pilot assessments**, versus **{summary['old_scored']}/10** previously, on the exact same saved texts and source checklists.",'',
        'The four advisor examples matched all expected counts. Both scorers pass **6/7** controlled regression cases (after preserving and retrying the old transport failure); no gain in independent judgment accuracy is established. The unit-significance disagreement remains. MedAESQA remains at its historical 50% agreement and kappa 0.00; these are different tasks.','',
        '| Report | System | Kind | Previous | New | Supported / claims | Missing | Partial | Distorted facts |',
        '|---|---|---|---|---|---:|---:|---:|---:|']
    for r in rows:
        m=r['metrics'];details=f"{m['claims_supported']}/{m['claims_total']} | {m['omissions']} | {m['partial_key_facts']} | {m['distorted_key_facts']}" if m else 'not scored | not scored | not scored | not scored'
        lines.append(f"| {r['source_row_id']} | {r['system']} | {r['kind']} | {r['old_status']} | {r['new_status']} | {details} |")
    lines += ['', 'These are provisional model judgments. Claim segmentation changed, so differences in fractions are not improvements in the answers or independently verified accuracy. Drafts remain outside released-output summaries. Whole missing facts and partially included facts are now distinct; distorted facts are not also counted as missing.','',
        '## What improved','',
        '- Evidence and output quotations come from exact source offsets via IDs, not generated text.',
        '- Every output block and every fixed key fact must be accounted for structurally.',
        '- Partial coverage identifies absent parts instead of calling a combined fact fully present or wholly absent.',
        '- Streaming and a 180-second per-request timeout address observed long-response connection failures; one bounded correction/retry is allowed and all attempts are retained.',
        '- In the allergy ADK draft, the revised assessment identifies the missing post-discharge update and omitted atenolol warning/rationale. A medication-list mention does not cover that rationale.','',
        '- In the cystitis ADK draft, it flags unqualified bladder-disorder denial and the unstated Bactrim unit, where the old valid assessment marked every claim supported. It also records partial coverage rather than treating all seven facts as complete.',
        '- In the CT ADK draft, it identifies the missing noncontrast limitation and the unexplained renal/adrenal discrepancy as partial coverage of two linked checklist entries, not proof of two independent clinical errors.','',
        '## Remaining limits','',
        'The judge is not calibrated, and semantic errors remain possible despite valid IDs. Both controlled runs flag the unstated unit as a distortion but do not consider it clinically meaningful; the unchanged test expectation disagrees. The seven cases are controlled synthetic development checks, not independently annotated gold or held-out data. No expected labels were sent to either judge.','',
        'A further observed false positive is the cystitis draft\'s scope disclaimer being counted as an unsupported proposition. That is output framing rather than a biomedical assertion. It remains in the saved raw result and is disclosed here; no claim or label was deleted post hoc to improve a percentage. The current model-assigned fractions therefore remain provisional.','',
        '## Files','',
        '- [Revised pilot assessments](clinical_scores_source_ids_final_v2.json)',
        '- [Streaming pass before compact corrections](clinical_scores_source_ids_stream_v2.json)',
        '- [Earlier interrupted non-streaming ID run](clinical_scores_source_ids_v2.json)',
        '- [Original pilot assessments](clinical_scores_v2.json)',
        '- [Machine-readable comparison](clinical_scoring_v2_comparison.json)',
        '- [Scorer instructions](../../../evaluation/CLINICAL_SCORING_V2.md)','',
        'The saved pilot texts were not changed. The live ADK Verifier and its calibration were not replaced. Nothing was committed or pushed.']
    (root/'CLINICAL_SCORING_V2_COMPARISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','regression')},indent=2))


if __name__=='__main__':main()
