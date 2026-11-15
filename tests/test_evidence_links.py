"""Source navigation must not manufacture evidence relationships."""
import pytest

from faithfulmed_ui.presentation import attributed_markdown, sources_html


def state(quote='The test found no cancer.'):
    return dict(source_report=quote, atoms=[{'source_quote': quote}],
                retrieved_context=[{'text': 'Background about exercise.',
                    'metadata': {'source_url': 'https://medlineplus.gov/exercise.html',
                                 'title': 'Exercise'}}])


@pytest.mark.parametrize('sentence', [
    'The test found cancer.',
    'Take an invented medication daily.',
    'The test found no cancer and you can stop your medication.',
    'There may be cancer.',
])
def test_overlap_contradictions_and_unmatched_claims_stay_unlinked(sentence):
    assert attributed_markdown(sentence, state()) == sentence
    without_pages = state()
    without_pages['retrieved_context'] = []
    assert attributed_markdown(sentence, without_pages) == sentence


def test_invalid_atom_quote_is_not_a_report_card_or_link():
    value = state()
    value['source_report'] = 'The current report says something else.'
    assert attributed_markdown('The test found no cancer.', value) == 'The test found no cancer.'
    assert 'report-quote-0' not in sources_html(value)


def test_missing_report_cannot_establish_quote_provenance():
    value = state()
    del value['source_report']
    assert attributed_markdown('The test found no cancer.', value) == 'The test found no cancer.'


def test_link_marker_preserves_bullets_bold_and_original_sentence():
    line = '- **Test:** The test found no cancer.'
    rendered = attributed_markdown(line, state())
    assert rendered.startswith(line + ' ')
    assert '[Report quote 1 (exact wording)](#report-quote-0)' in rendered
    assert r'\*\*' not in rendered
    assert not rendered.startswith('[-')


def test_multiple_sentences_are_not_given_one_partial_evidence_link():
    text = 'The test found no cancer. Stop taking your medication.'
    assert attributed_markdown(text, state()) == text


def test_headings_and_code_are_not_annotated():
    text = '# The test found no cancer.\n```text\nThe test found no cancer.\n```'
    assert attributed_markdown(text, state()) == text


def test_quote_ids_are_deduplicated_and_only_use_current_report():
    value = state()
    value['atoms'] *= 2
    html = sources_html(value)
    assert html.count('id="report-quote-0"') == 1
    assert 'report-quote-1' not in html
    assert 'exact wording, not independent clinical validation' in html
    assert html.index('Report quote 1') < html.index('general medical background')


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'https://medlineplus.gov.evil.example/path',
    'https://evil.example/medlineplus.gov', 'https://[invalid',
    'https://user:password@medlineplus.gov/path',
    'https://medlineplus.gov:9999/path',
    'https://medlineplus.gov/path) [unsafe](javascript:alert(1))',
    'https://medlineplus.gov/path\nmalformed',
])
def test_invalid_metadata_urls_are_not_clickable(url):
    value = dict(retrieved_context=[{'text': 'Background',
                                   'metadata': {'source_url': url}}])
    assert 'href=' not in sources_html(value)


def test_valid_medlineplus_source_stays_clickable_and_text_is_escaped():
    value = state()
    value['retrieved_context'][0]['text'] = '<script>example</script>'
    html = sources_html(value)
    assert 'href="https://medlineplus.gov/exercise.html"' in html
    assert '&lt;script&gt;' in html
    assert '<script>' not in html
