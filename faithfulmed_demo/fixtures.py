"""Explicitly scripted walkthrough, limited to the existing chest-pain example."""

import json

from .config import ROOT

EXAMPLE = json.loads((ROOT / 'baseline/examples/synthetic_chest_pain.json').read_text(encoding='utf-8'))
SOURCE = EXAMPLE['clinical_text']
QUOTES = [sentence + '.' for sentence in SOURCE.split('. ')[:-1]] + [SOURCE.split('. ')[-1]]
ATOMS = [
    {'text': quote, 'type': kind, 'assertion': assertion, 'source_quote': quote}
    for quote, kind, assertion in zip(QUOTES,
        ['symptom', 'lab_value', 'procedure', 'lab_value', 'diagnosis', 'instruction', 'medication'],
        ['affirmed', 'negated', 'pending', 'uncertain', 'affirmed', 'affirmed', 'conditional'])
]
CONTEXT = [{
    'id': '69992f9cf5637668868cfecc553327eeaba51f5e5b6baddaf97d764bf2b81880',
    'text': 'Having a pain in your chest can be scary. It does not always mean that you are having a heart attack . There can be many other causes, including: Other heart problems, such as angina Panic attacks Digestive problems, such as heartburn or esophagus disorders Sore muscles Lung diseases, such as pneumonia , pleurisy , or pulmonary embolism Costochondritis - an inflammation of joints in your chest Some of these problems can be serious. Get immediate medical care if you have chest pain that does not go away, crushing pain or pressure in the chest, or chest pain along with nausea, sweating, dizziness or shortness of breath. Treatment depends on the cause of the pain.',
    'metadata': {'source_url': 'https://medlineplus.gov/chestpain.html', 'title': 'Chest Pain'},
    'distance': None,
}]
DRAFT = ('You came to the hospital with chest pain. Your blood tests did not show a heart attack. '
         'Your stress test was done, but the result is not back yet. Your liver test levels were high. '
         'The cause is not yet known. You also have acid reflux. '
         'See your heart doctor in two weeks and your main doctor in two to four weeks. '
         'Your medicines will depend on the stress test result.')
BAD_CLAIM = 'You have pneumonia.'


def fixture_verdict(draft):
    # This checks ONLY the deliberate demonstration claim, not arbitrary medicine.
    issues = []
    if BAD_CLAIM in draft:
        issues.append({'category': 'unsupported', 'claim': BAD_CLAIM,
                       'reason': 'Pneumonia is listed as a possible general cause in MedlinePlus, but is not diagnosed in this note.',
                       'source_quote': QUOTES[0], 'replacement': ''})
    return {'issues': issues, 'supported_examples': [QUOTES[1]],
            'scope': 'Scripted fixture check only; not a clinical verifier.'}
