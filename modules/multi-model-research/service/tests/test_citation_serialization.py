import json

import pytest

from workflow import citations


@pytest.mark.parametrize('separator', ['\n- ', '\n\n## Heading\n', '\t', '\r\n'])
def test_json_report_scans_decoded_text_instead_of_escape_sequences(separator):
    value = {'report': 'https://example.org/source' + separator + 'https://other.example/source'}
    text = 'Narrative.\n\n```json\n' + json.dumps(value) + '\n```\n'
    assert citations(text) == ['https://example.org/source', 'https://other.example/source']


@pytest.mark.parametrize('label', ['json', 'evidence-ledger'])
def test_preserved_nested_report_json_does_not_create_phantom_urls(label):
    inner = '```json\n' + json.dumps({'report': 'https://example.org/a\n- item'}) + '\n```\n'
    document = 'https://outside.example/b\n```' + label + '\n' + json.dumps({'report': inner}) + '\n```\n'
    assert citations(document) == ['https://outside.example/b', 'https://example.org/a']


def test_complete_json_and_escaped_slashes_unicode_are_decoded_exactly():
    text = r'{"report":"https:\/\/example.org\/source\nhttps:\u002f\u002finvented.example\/bad"}'
    assert citations(text) == ['https://example.org/source', 'https://invented.example/bad']


def test_unknown_source_after_escaped_newline_is_not_hidden():
    text = json.dumps({'report': 'https://allowed.example/source\nhttps://invented.example/source'})
    assert set(citations(text)) - {'https://allowed.example/source'} == {'https://invented.example/source'}


def test_literal_backslashes_outside_json_and_percent_encoded_paths_are_not_rewritten():
    raw = r'https://example.org/source\n-'
    assert citations(raw) == [raw]
    url = 'https://example.org/%5Cn?q=%22value%22#section'
    assert citations(json.dumps({'url': url})) == [url]


def test_all_duplicate_json_keys_and_values_are_scanned_not_overwritten():
    text = r'{"url":"https:\/\/allowed.example\/a","url":"https:\/\/invented.example\/b"}'
    assert citations(text) == ['https://allowed.example/a', 'https://invented.example/b']


def test_json_keys_and_text_after_valid_fence_remain_visible():
    text = '```json\n' + json.dumps({'https://key.example/a': 'https://value.example/b'}) + '\n```\nhttps://after.example/c'
    assert citations(text) == ['https://key.example/a', 'https://value.example/b', 'https://after.example/c']


def test_malformed_fences_and_non_json_code_keep_original_scanning():
    for text in ['```json\n{"report": "https://invented.example/b"\n```',
                 '```python\nhttps://invented.example/b\n```']:
        assert citations(text) == ['https://invented.example/b']


def test_nested_markdown_link_boundaries_are_respected_after_decoding():
    text = json.dumps({'report': '[First](https://example.org/Function_(x))–[Next](https://example.org/next)'})
    assert citations(text) == ['https://example.org/Function_(x)', 'https://example.org/next']


def test_array_and_repeated_urls_preserve_first_seen_order():
    text = json.dumps(['https://one.example/a\n- ', {'r': 'https://two.example/b'}, 'https://one.example/a'])
    assert citations(text) == ['https://one.example/a', 'https://two.example/b']
