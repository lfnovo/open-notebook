"""Guarantees for the browser research path.

The invariant under test throughout: a research submission is never sent twice, and
an ordinary chat answer is never accepted in place of a real research report.
"""
import asyncio
import json
from pathlib import Path
import sys
import uuid
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parents[1]))
from browser_research import BrowserResearch
from browser_runtime import BrowserAttention
from engine import Engine
from store import Store
from workflow import STAGES, digest, prompt_for
from fakes import FakePage, FakeRuntime, el

RUN = 'a' * 32
STAGE = {'id': 'research_chatgpt', 'provider': 'ChatGPT'}
LONG = 'Research finding with primary evidence. ' * 60 + ' https://example.org/source'


async def noop(_value):
    return None


def build(page, entry=None, **kwargs):
    runtime = FakeRuntime(page, research_entry=entry)
    return BrowserResearch(runtime, kwargs.pop('root'), poll_seconds=0, confirm_seconds=2,
                           upload_seconds=2, **kwargs), runtime


def composer(page):
    page.add(el(sel=['#prompt-textarea'], text=''))
    page.add(el(sel=['[data-testid="send-button"]'], role='button', name='Send'))
    return page


def assistant(page, text, name='report'):
    return page.add(el(sel=['[data-message-author-role="assistant"]'], text=text))


# --------------------------------------------------------------------------
# Research mode must be observably engaged, or nothing is sent.
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_research_mode_never_sends_an_ordinary_chat(tmp_path):
    page = composer(FakePage())
    browser, _ = build(page, entry=None, root=tmp_path)
    with pytest.raises(BrowserAttention) as exc:
        await browser.research(RUN, STAGE, 'question', noop)
    assert exc.value.kind == 'research_unavailable'
    assert page.filled == [] and page.clicks == []
    assert browser.load(RUN, STAGE['id'])['phase'] == 'prepared'


@pytest.mark.asyncio
async def test_research_label_present_but_not_selected_is_refused(tmp_path):
    page = composer(FakePage())
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    # The control exists and is clicked, but nothing reports a selected state.
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    with pytest.raises(BrowserAttention) as exc:
        await browser.research(RUN, STAGE, 'question', noop)
    assert exc.value.kind == 'browser_changed'
    assert 'seçili olduğu doğrulanamadı' in str(exc.value)
    assert page.filled == []


def browser_entry(page, element):
    from fakes import Loc
    return Loc(page, [element])


@pytest.mark.asyncio
async def test_an_explicit_not_selected_state_blocks_the_send(tmp_path):
    # The provider reports the control as off while a chip-shaped element also exists.
    # The veto must win and nothing may be submitted.
    page = composer(FakePage(selected_mode='', selected_negative=True, chip=True))
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    with pytest.raises(BrowserAttention) as exc:
        await browser.research(RUN, STAGE, 'question', noop)
    assert exc.value.kind == 'browser_changed'
    assert 'Send' not in page.clicks and page.filled == []
    assert browser.load(RUN, STAGE['id'])['phase'] == 'prepared'


# --------------------------------------------------------------------------
# The submission journal is written immediately before the click, never earlier.
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_before_the_click_leaves_the_job_safely_retryable(tmp_path):
    page = FakePage(selected_mode='aria-pressed')
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    # No composer at all: preparation fails after the mode was engaged.
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    with pytest.raises(Exception):
        await browser.research(RUN, STAGE, 'question', noop)
    job = browser.load(RUN, STAGE['id'])
    assert job['phase'] == 'prepared', 'a job that never reached the send button must stay retryable'
    assert 'Send' not in page.clicks


@pytest.mark.asyncio
async def test_uncertain_send_is_never_replayed(tmp_path):
    page = composer(FakePage(selected_mode='aria-pressed'))
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    # The click lands but the conversation never identifies itself, and reconcile finds nothing.
    with pytest.raises(BrowserAttention) as exc:
        await browser.research(RUN, STAGE, 'question', noop)
    assert exc.value.kind == 'submission_uncertain'
    assert page.clicks.count('Send') == 1
    assert browser.load(RUN, STAGE['id'])['phase'] == 'submit_unconfirmed'

    # A second attempt must reconcile, not resend.
    with pytest.raises(BrowserAttention) as again:
        await browser.research(RUN, STAGE, 'question', noop)
    assert again.value.kind == 'submission_uncertain'
    assert page.clicks.count('Send') == 1, 'the same research was submitted twice'


@pytest.mark.asyncio
async def test_reconcile_adopts_the_existing_conversation_instead_of_resending(tmp_path):
    page = composer(FakePage(selected_mode='aria-pressed'))
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    with pytest.raises(BrowserAttention):
        await browser.research(RUN, STAGE, 'question', noop)
    assert page.clicks.count('Send') == 1
    job = browser.load(RUN, STAGE['id'])

    # The provider does have our submission after all; it carries the job marker.
    page.add(el(sel=['[data-message-author-role="user"]'], text='question ' + job['marker']))
    page.url = 'https://chatgpt.com/c/abc123'
    assistant(page, 'Research completed. Findings with sources https://example.org/a ' + LONG)
    result = await browser.research(RUN, STAGE, 'question', noop)
    assert page.clicks.count('Send') == 1, 'reconcile must adopt the run, not start a new one'
    assert 'example.org' in result['content']
    assert browser.load(RUN, STAGE['id'])['phase'] == 'completed'


@pytest.mark.asyncio
async def test_changed_input_packet_does_not_resubmit(tmp_path):
    page = composer(FakePage(selected_mode='aria-pressed'))
    entry = page.add(el(sel=['research-entry'], role='button', name='Deep research'))
    browser, _ = build(page, entry=browser_entry(page, entry), root=tmp_path)
    with pytest.raises(BrowserAttention):
        await browser.research(RUN, STAGE, 'question', noop)
    with pytest.raises(BrowserAttention) as exc:
        await browser.research(RUN, STAGE, 'a different question', noop)
    assert exc.value.kind == 'submission_uncertain'
    assert page.clicks.count('Send') == 1


# --------------------------------------------------------------------------
# A report counts only with completion evidence and external sources.
# --------------------------------------------------------------------------
def completed_job(browser, url='https://chatgpt.com/c/x'):
    job = {'phase': 'submitted', 'provider': 'ChatGPT', 'prompt_sha256': digest('q'),
           'created_at': 'now', 'marker': 'ON-x', 'url': url, 'research_started': True}
    browser.save(RUN, STAGE['id'], job)
    return job


@pytest.mark.asyncio
async def test_plain_answer_without_completion_evidence_is_not_a_report(tmp_path):
    page = FakePage(url='https://chatgpt.com/c/x')
    assistant(page, LONG)  # long, stable, cited - but nothing says research finished
    browser, _ = build(page, root=tmp_path)
    job = completed_job(browser)
    job['research_started'] = False
    assert await browser.collect(page, 'ChatGPT', job) is None


@pytest.mark.asyncio
async def test_completion_wording_in_the_user_prompt_does_not_count(tmp_path):
    page = FakePage(url='https://chatgpt.com/c/x')
    # Our own prompt says the phrase. Only the assistant's output may prove completion.
    page.add(el(sel=['[data-message-author-role="user"]'], text='araştırma tamamlandı diye yazma'))
    assistant(page, LONG)
    browser, _ = build(page, root=tmp_path)
    job = completed_job(browser)
    job['research_started'] = False
    assert await browser.collect(page, 'ChatGPT', job) is None


@pytest.mark.asyncio
async def test_report_without_external_sources_is_rejected(tmp_path):
    page = FakePage(url='https://chatgpt.com/c/x')
    assistant(page, 'Research complete. ' + 'Internal only https://chatgpt.com/c/x ' * 60)
    browser, _ = build(page, root=tmp_path)
    with pytest.raises(BrowserAttention):
        await browser.collect(page, 'ChatGPT', completed_job(browser))


@pytest.mark.asyncio
async def test_streaming_response_is_never_collected(tmp_path):
    page = FakePage(url='https://chatgpt.com/c/x')
    assistant(page, 'Research complete. ' + LONG)
    page.add(el(sel=['button[data-testid="stop-button"]'], role='button', name='Stop'))
    browser, _ = build(page, root=tmp_path)
    assert await browser.collect(page, 'ChatGPT', completed_job(browser)) is None


@pytest.mark.asyncio
async def test_completed_job_is_served_from_the_journal_without_touching_the_page(tmp_path):
    page = FakePage(url='https://chatgpt.com/c/x')
    browser, runtime = build(page, root=tmp_path)
    folder = browser.folder(RUN, STAGE['id'])
    (folder / 'report.md').write_text(LONG)
    browser.save(RUN, STAGE['id'], {'phase': 'completed', 'provider': 'ChatGPT',
                                    'prompt_sha256': digest('question'), 'url': 'https://chatgpt.com/c/x',
                                    'report_sha256': digest(LONG), 'marker': 'ON-x'})
    result = await browser.research(RUN, STAGE, 'question', noop)
    assert result['content'] == LONG
    assert runtime.checks == 0 and page.clicks == []


@pytest.mark.asyncio
async def test_tampered_stored_report_is_refused(tmp_path):
    page = FakePage()
    browser, _ = build(page, root=tmp_path)
    folder = browser.folder(RUN, STAGE['id'])
    (folder / 'report.md').write_text('replaced content')
    browser.save(RUN, STAGE['id'], {'phase': 'completed', 'provider': 'ChatGPT',
                                    'prompt_sha256': digest('question'), 'url': 'u',
                                    'report_sha256': digest(LONG), 'marker': 'ON-x'})
    with pytest.raises(BrowserAttention):
        await browser.research(RUN, STAGE, 'question', noop)


# --------------------------------------------------------------------------
# Engine-level behaviour for browser runs.
# --------------------------------------------------------------------------
class StubBrowser:
    def __init__(self, root, resumable=True):
        self.root = Path(root)
        self.resumable = resumable
        self.calls = []

    def can_resume(self, run_id, stage_id):
        return self.resumable

    def artifacts(self, run_id, stage_id):
        folder = self.root / 'browser_jobs' / run_id / stage_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'report.md'
        path.write_text('browser report body')
        return [path]

    async def research(self, run_id, stage, prompt, progress):
        self.calls.append(stage['id'])
        await progress({'phase': 'researching'})
        return {'content': 'Browser report ' + stage['id'] + ' https://example.org/x',
                'url': 'https://chatgpt.com/c/' + stage['id']}

    async def close(self):
        pass


class Sink:
    def __init__(self):
        self.notes = {}

    async def notebook(self, run):
        return 'notebook:test'

    async def note(self, run, stage):
        self.notes.setdefault((run['id'], stage['id']), 'note:' + stage['id'])
        return self.notes[(run['id'], stage['id'])]


class Provider:
    def __init__(self):
        self.calls = []

    async def synthesize(self, stage, prompt):
        self.calls.append(stage['id'])
        return 'Synthesis ' + stage['id'] + ' https://example.org/s', {}


@pytest_asyncio.fixture
async def browser_engine(tmp_path):
    store = Store(tmp_path)
    await store.open()
    engine = Engine(store, Provider(), Sink(), lambda t: len(t) // 4, 90000,
                    browser=StubBrowser(tmp_path))
    yield engine
    await engine.close()
    await store.close()


async def settle(engine):
    for _ in range(400):
        if not engine.tasks and not engine.background:
            return
        await asyncio.sleep(.01)
    raise AssertionError('tasks did not settle')


@pytest.mark.asyncio
async def test_one_question_drives_all_five_web_stages_then_synthesis(browser_engine):
    run = await browser_engine.create(
        {'question': 'Tek soru ile tam akış', 'scope': '', 'language': 'Türkçe',
         'auto_synthesize': True, 'execution_mode': 'browser'}, uuid.uuid4().hex)
    await settle(browser_engine)
    final = await browser_engine.get(run['id'])
    assert final['status'] == 'completed'
    assert browser_engine.browser.calls == ['research_gemini', 'research_chatgpt', 'research_claude',
                                            'review_chatgpt', 'review_claude']
    assert browser_engine.provider.calls == ['synthesis_chatgpt', 'synthesis_claude', 'final_chatgpt']
    assert len(browser_engine.sink.notes) == 8


@pytest.mark.asyncio
async def test_auto_synthesize_off_still_runs_web_research_but_holds_synthesis(browser_engine):
    run = await browser_engine.create(
        {'question': 'Yalnız araştırma', 'scope': '', 'language': 'Türkçe',
         'auto_synthesize': False, 'execution_mode': 'browser'}, uuid.uuid4().hex)
    await settle(browser_engine)
    assert len(browser_engine.browser.calls) == 5
    assert browser_engine.provider.calls == []


@pytest.mark.asyncio
async def test_interrupted_browser_stage_resumes_but_account_stage_does_not(browser_engine):
    run = await browser_engine.create(
        {'question': 'Kurtarma', 'scope': '', 'language': 'Türkçe',
         'auto_synthesize': False, 'execution_mode': 'browser'}, uuid.uuid4().hex)
    await settle(browser_engine)
    stored = await browser_engine.get(run['id'])
    stored['stages'][0]['status'] = 'interrupted'
    stored['stages'][5]['status'] = 'interrupted'
    stored['stages'][5]['mode'] = 'account'
    await browser_engine.store.save(stored)
    browser_engine.browser.calls.clear()
    await browser_engine.recover()
    await settle(browser_engine)
    after = await browser_engine.get(run['id'])
    assert browser_engine.browser.calls == ['research_gemini'], 'browser job must resume itself'
    assert after['stages'][5]['status'] == 'interrupted', 'an account call must never auto-repeat'


@pytest.mark.asyncio
async def test_browser_report_records_its_job_files_for_export(browser_engine):
    run = await browser_engine.create(
        {'question': 'Dışa aktarma', 'scope': '', 'language': 'Türkçe',
         'auto_synthesize': False, 'execution_mode': 'browser'}, uuid.uuid4().hex)
    await settle(browser_engine)
    stage = (await browser_engine.get(run['id']))['stages'][0]
    files = stage['report']['browser_files']
    assert files and files[0]['name'] == 'report.md'
    assert (browser_engine.store.root / files[0]['path']).is_file()
    assert stage['report']['provenance'] == 'browser_deep_research'
