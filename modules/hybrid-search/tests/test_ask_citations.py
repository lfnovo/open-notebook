"""Citation scope is a property of the answer, not of the retrieval backend."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import ask
from open_notebook.modules.hybrid_search import service


class Record:
    """A record id that is not a plain string, as the database layer can return."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def answer_model(monkeypatch, text):
    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=MagicMock(content=text))
    monkeypatch.setattr(ask, 'provision_langchain_model', AsyncMock(return_value=model))


def use_legacy_vector_path(monkeypatch, results):
    monkeypatch.setattr(ask.SearchAdapter, 'enabled', lambda: False)
    monkeypatch.setattr(ask, 'vector_search', AsyncMock(return_value=results))


STATE = {'question': 'q', 'term': 't', 'instructions': 'i', 'notebook_ids': []}


@pytest.mark.asyncio
async def test_disabled_module_still_rejects_an_unretrieved_citation(monkeypatch):
    # Turning the hybrid module off used to turn this check off with it.
    use_legacy_vector_path(monkeypatch, [{'id': 'note:a'}])
    answer_model(monkeypatch, 'Invented [note:elsewhere]')
    with pytest.raises(ExternalServiceError):
        await ask.provide_answer(dict(STATE), {'configurable': {}})


@pytest.mark.asyncio
async def test_disabled_module_accepts_a_retrieved_citation(monkeypatch):
    use_legacy_vector_path(monkeypatch, [{'id': 'note:a'}])
    answer_model(monkeypatch, 'Supported [note:a]')
    value = await ask.provide_answer(dict(STATE), {'configurable': {}})
    assert value['answers'] == ['Supported [note:a]']


@pytest.mark.asyncio
async def test_record_ids_compare_by_their_text(monkeypatch):
    use_legacy_vector_path(monkeypatch, [{'id': Record('note:a')}])
    answer_model(monkeypatch, 'Supported [note:a]')
    value = await ask.provide_answer(dict(STATE), {'configurable': {}})
    assert value['answers'] == ['Supported [note:a]']


@pytest.mark.asyncio
async def test_empty_answer_still_reports_retrieval_diagnostics(monkeypatch):
    monkeypatch.setattr(ask.SearchAdapter, 'enabled', lambda: True)
    engine = MagicMock()
    engine.search = AsyncMock(return_value=([{'id': 'note:a'}], {'warnings': ['weak_relevance']}))
    monkeypatch.setattr(ask.SearchAdapter, 'engine', lambda: engine)
    monkeypatch.setattr(service, 'settings', lambda: service.DEFAULTS.copy())
    answer_model(monkeypatch, '   ')
    value = await ask.provide_answer(dict(STATE), {'configurable': {}})
    assert value['answers'] == []
    assert value['retrieval'] == [{'warnings': ['weak_relevance']}], 'the diagnostic was dropped'


def test_final_answer_may_only_reuse_a_validated_citation():
    ask.validate_citations('Final [note:a]', ask.CITATION.findall('Partial [note:a]'))
    with pytest.raises(ExternalServiceError):
        ask.validate_citations('Final [note:b]', ask.CITATION.findall('Partial [note:a]'))
