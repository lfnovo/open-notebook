import pytest

from workflow import citations


@pytest.mark.parametrize('separator', ['–','—','-',' → ','; ',': '])
def test_adjacent_markdown_links_do_not_absorb_sentence_punctuation(separator):
    text='[First](https://example.org/first)'+separator+'[Second](https://example.org/second)'
    assert citations(text)==['https://example.org/first','https://example.org/second']


def test_balanced_parentheses_in_markdown_destination_are_preserved():
    assert citations('[Wiki](https://example.org/Function_(mathematics))–[Next](https://example.org/next)')==[
        'https://example.org/Function_(mathematics)','https://example.org/next']


def test_query_fragment_unicode_and_bare_internal_parenthesis_are_not_rewritten():
    values=['https://example.org/foo)bar','https://example.org/é–test?q=x&fields=title,year#part']
    assert citations(' '.join(values))==values
    assert citations('[Source]('+values[1]+')')==[values[1]]


def test_boundary_fix_does_not_turn_a_different_source_into_an_allowed_url():
    assert citations('[Bad](https://example.org/other)–[Source](https://example.org/source)')==[
        'https://example.org/other','https://example.org/source']


@pytest.mark.parametrize('placeholder', ['https://…','https://…”','https://...','http://...'])
def test_ellipsis_only_example_is_not_a_source_address(placeholder):
    assert citations('The field contains a placeholder: '+placeholder+' .') == []


def test_real_host_with_ellipsis_path_is_not_silently_removed():
    assert citations('https://example.org/… https://invented.org/source') == [
        'https://example.org/…','https://invented.org/source']
