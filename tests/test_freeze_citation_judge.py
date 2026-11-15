from copy import deepcopy
from unittest.mock import patch

import pytest

from evaluation import freeze_citation_judge as frozen
from evaluation.scoring import digest


def manifest(spec):
    return dict(fingerprint=digest(spec),specification=deepcopy(spec))


def test_changed_prompt_or_policy_is_detected():
    spec=dict(prompt='fixed',policy={'attempts':2})
    saved=manifest(spec)
    with pytest.raises(ValueError,match='drift'):
        frozen.verify_manifest(saved,dict(prompt='changed',policy={'attempts':2}))
    altered=deepcopy(saved)
    altered['specification']['policy']['attempts']=3
    with pytest.raises(ValueError,match='edited or corrupted'):
        frozen.verify_manifest(altered,spec)


def test_freeze_is_idempotent_and_never_overwrites_different_settings(tmp_path,monkeypatch):
    target=tmp_path/'manifest.json'
    monkeypatch.setattr(frozen,'MANIFEST',target)
    monkeypatch.setattr(frozen,'current_specification',lambda:{'prompt':'fixed'})
    first=frozen.freeze();before=target.read_bytes()
    assert frozen.freeze()==first
    assert target.read_bytes()==before
    monkeypatch.setattr(frozen,'current_specification',lambda:{'prompt':'different'})
    with pytest.raises(ValueError,match='drift'):
        frozen.freeze()
    assert target.read_bytes()==before


def test_missing_freeze_stops_before_model_call(tmp_path,monkeypatch):
    monkeypatch.setattr(frozen,'MANIFEST',tmp_path/'absent.json')
    with patch.object(frozen.evaluator,'judge') as call:
        with pytest.raises(ValueError,match='Freeze the configuration'):
            frozen.judge({})
    call.assert_not_called()


def test_frozen_configuration_still_requires_a_bound_cohort():
    with patch.object(frozen,'verify',return_value={'fingerprint':'configuration'}), \
         patch.object(frozen.evaluator,'judge') as call:
        with pytest.raises(ValueError,match='Freeze the evaluation cohort'):
            frozen.judge({})
    call.assert_not_called()


def test_bound_cohort_rejects_changed_labels_and_source_text():
    case=dict(case_id='case',question='Question?',sentence='Statement.',evidence='Document.',
              reference_relation='supporting',reference_support=True)
    spec=dict(configuration_fingerprint='configuration',sampling_policy='declared sample',
              exclusions_sha256='audit digest',case_records={'case':dict(
                  payload_sha256=digest(frozen.evaluator.strict.original.judge_payload(case)),
                  reference_sha256=digest({'reference_relation':'supporting','reference_support':True}))})
    cohort=manifest(spec)
    frozen.verify_cohort(case,cohort,'configuration')
    for modified in [dict(case,evidence='Changed document.'),dict(case,reference_support=False)]:
        with pytest.raises(ValueError,match='differ from the frozen cohort'):
            frozen.verify_cohort(modified,cohort,'configuration')


@pytest.mark.parametrize('attempt,used,expected',[
    ({'status':'ok','supports_sentence':False},1,False),
    ({'status':'error','failure_code':'ambiguous_quote_location'},1,True),
    ({'status':'error','failure_code':'quote_not_in_document'},2,False),
    ({'status':'error','service_code':429},1,False),
    ({'status':'error','service_code':403,'failure_code':'schema_validation'},1,False),
    ({'status':'error','service_code':503},1,True),
    ({'status':'error','error_type':'ReadTimeout'},1,True),
    ({'status':'started'},1,False),
])
def test_retry_budget_and_access_stop_rules(attempt,used,expected):
    policy=dict(max_attempts_per_case=2,stop_http_codes=[400,401,403,404,429],
        retryable_failure_codes=['ambiguous_quote_location','quote_not_in_document','schema_validation'],
        transient_http_codes=[503],transient_error_types=['ReadTimeout'])
    assert frozen.retry_allowed(attempt,used,policy) is expected


def test_snapshot_normalizes_only_line_endings(tmp_path,monkeypatch):
    monkeypatch.setattr(frozen,'SOURCE_FILES',('code.py',))
    path=tmp_path/'code.py'
    path.write_bytes(b'first\r\nsecond\r\n')
    initial=frozen.source_snapshot(tmp_path)
    path.write_bytes(b'first\nsecond\n')
    assert frozen.source_snapshot(tmp_path)==initial
    path.write_bytes(b'first\nchanged\n')
    assert frozen.source_snapshot(tmp_path)!=initial
