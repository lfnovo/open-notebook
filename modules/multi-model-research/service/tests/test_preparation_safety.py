"""Regressions: an archive sidecar is not evidence delivered to the next model."""
from context_compaction import compact_packet, expand_prompt
from packet_markdown import markdown_packet


def packet(text):
    return {'question': 'Which method?', 'scope': '', 'reports': [{
        'stage': 'research_chatgpt', 'content': text, 'evidence': [], 'citations': []}]}


def test_unique_qualifications_are_never_deleted_to_meet_a_budget():
    original = packet('The method is effective.\nThis applies only to adults.\n'
                      'It must never be used in children.\nI cannot verify the source.\n')
    result = compact_packet(original, 1, len)
    assert result['packet'] == original
    assert expand_prompt(result['prompt']) == markdown_packet(original)
    assert not result['fits']


def test_crlf_and_unicode_survive_without_an_external_restore_sidecar():
    original = packet('İstisna: çocuklarda kullanılmaz.\r\nYalnız yetişkinler.\r\n')
    result = compact_packet(original, 1, len)
    assert result['packet'] == original
    assert expand_prompt(result['prompt']) == markdown_packet(original)


def test_removing_context_cannot_change_a_retained_claims_meaning():
    original = packet('The following assertion is false.\nThe treatment is safe.\n')
    result = compact_packet(original, 1, len)
    assert markdown_packet(original) == markdown_packet(result['packet'])
