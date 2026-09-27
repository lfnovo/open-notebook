import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResearchRun, ResearchStage } from '@/modules/multi-model-research/api'
import { researchEn } from '@/modules/multi-model-research/locales'
import { ResearchRetryPanel, retryTiming } from './ResearchRetryPanel'
import { ResearchQuestionCard } from './ResearchQuestionCard'
import { ResearchWorkflow } from './ResearchWorkflow'
import { ResearchAttentionSummary, ResearchStopFeedback } from './ResearchStopFeedback'
import { ResearchPolicyPanel } from './ResearchPolicyPanel'
import { ContextBudgetRows, PacketBudget, PacketCompaction, SharedEvidencePacket } from './ResearchContextBudget'

vi.mock('@/lib/hooks/use-translation', () => ({ useTranslation: () => ({ language: 'en-US', t: (key: string, values: Record<string, unknown> = {}) => {
  const value = key === 'common.close' ? 'Close' : researchEn[key.replace('research.', '') as keyof typeof researchEn] || key
  return Object.entries(values).reduce((text, [name, replacement]) => text.replaceAll('{{' + name + '}}', String(replacement)), value)
} }) }))

const now = Date.parse('2026-09-21T12:00:00Z')
function makeStage(overrides: Partial<ResearchStage> = {}): ResearchStage {
  return { id: 'synthesis_chatgpt', provider: 'ChatGPT', round: 3, mode: 'account', status: 'failed', attempts: 2, report: null, error: null, usage: null, note_id: null, browser_progress: null, retry_index: 2, next_retry_at: new Date(now + 300_000).toISOString(), ...overrides }
}
function makeRun(stage: ResearchStage, overrides: Partial<ResearchRun> = {}): ResearchRun {
  return { id: 'test-run', question: '# A long research question\n\n**Important evidence**\n\n' + 'Context to preserve. '.repeat(200) + '\n\nThe final sentence is retained.', scope: '## Scope\n\n- Primary sources\n- Dates', as_of: '2026-09-21', language: 'English', auto_synthesize: true, execution_mode: 'browser', paused: false, status: 'needs_attention', stages: [stage], created_at: new Date(now).toISOString(), updated_at: new Date(now).toISOString(), notebook_id: null, sync_error: null, ...overrides }
}

afterEach(() => { cleanup(); vi.useRealTimers() })

describe('Input budget transparency',()=>{
  it('labels projections and missing report reserves without triggering an action',()=>{
    const select=vi.fn()
    render(<ContextBudgetRows onSelect={select} rows={[{stage_id:'final_chatgpt',provider:'ChatGPT',round:4,warning:true,projection:true,missing_reports:2,reserved_report_tokens:64000,counted_tokens:190000,automatic_input_limit:180000,fits:false}]}/> )
    expect(screen.getByText('Projection; not an actual input count')).toBeInTheDocument()
    expect(screen.getByText(/2 missing reports/)).toBeInTheDocument()
    expect(screen.getByText('Exceeds the estimated input budget')).toBeInTheDocument()
    expect(select).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button'))
    expect(select).toHaveBeenCalledWith('final_chatgpt')
  })
  it('distinguishes raw tokens, transport and margin instead of claiming exact provider usage',()=>{
    render(<PacketBudget packet={{prompt:'full',sha256:'hash',report_count:7,estimated_tokens:177746,automatic_input_limit:180000,raw_tokens:150000,transport_raw_tokens:151000,counted_tokens:177746,effective_raw_limit:152960,remaining_input_tokens:2254,token_margin:{multiplier:1.15,overhead_tokens:4096,basis:'local'}}}/> )
    expect(screen.getByText('Raw packet tokens (o200k_base)')).toBeInTheDocument()
    expect(screen.getByText('Raw CLI input tokens')).toBeInTheDocument()
    expect(screen.getByText(/not an exact provider-tokenizer measurement/)).toBeInTheDocument()
  })
})

const AUDIT={before_tokens:182202,after_tokens:180304,saved_tokens:1898,removed_sentences:0,
  referenced_blocks:12,candidates:12,round_raw_limit:114927,fits:false,marker:'reference',
  by_reason:{exact_reference:325},by_stage:{}}

describe('Evidence preparation is explicit',()=>{
  it('describes in-band references without claiming deleted prose is lossless',()=>{
    render(<PacketCompaction audit={AUDIT}/> )
    expect(screen.getByText('Evidence preparation')).toBeInTheDocument()
    expect(screen.getByText(/No unique sentence is removed/)).toBeInTheDocument()
    expect(screen.getByText('12 shared blocks · 1,898 tokens saved')).toBeInTheDocument()
  })
  it('shows the complete multi-pass plan, quota impact and semantic limitation',()=>{
    render(<PacketCompaction preparation={{version:'v1',parts:4,minimum_calls:5,source_bytes:100,source_sha256:'hash',coverage_verified:true,semantic_lossless:false,status:'planned'}}/> )
    expect(screen.getByText('Read the complete evidence in 4 parts')).toBeInTheDocument()
    expect(screen.getByText(/byte coverage does not guarantee/)).toBeInTheDocument()
    expect(screen.getByText(/At least 5 account calls/)).toBeInTheDocument()
  })
  it('hides an unused preparation panel',()=>{
    const {container}=render(<PacketCompaction audit={null}/> )
    expect(container).toBeEmptyDOMElement()
  })
  it('distinguishes fresh re-research from source-only synthesis and exposes its progress',()=>{
    render(<PacketCompaction preparation={{version:'account-review-v1',parts:3,minimum_calls:4,source_bytes:100,source_sha256:'hash',coverage_verified:true,semantic_lossless:false,status:'checking_sources',current:'P2',completed_calls:2}}/> )
    expect(screen.getByText('Account re-research')).toBeInTheDocument()
    expect(screen.getByText(/Checking quoted passages against public sources/)).toBeInTheDocument()
    expect(screen.getByText(/not factual truth/)).toBeInTheDocument()
    expect(screen.getByText('P2')).toBeInTheDocument()
    expect(screen.queryByText(/Continue this stage to begin/)).not.toBeInTheDocument()
  })
})

describe('Recorded stop reasons', () => {
  it('shows the exact provider failure instead of inventing a root cause', () => {
    render(<ResearchStopFeedback stage={makeStage({ error: 'CLI exited with status 7: provider unavailable' })} />)
    expect(screen.getByText('CLI exited with status 7: provider unavailable')).toBeInTheDocument()
    expect(screen.getByText('Completed reports and sources remain saved.')).toBeInTheDocument()
    expect(screen.queryByText(/timeout/i)).not.toBeInTheDocument()
  })
  it('states that a missing reason is unknown', () => {
    render(<ResearchStopFeedback stage={makeStage({ error: '  ' })} />)
    expect(screen.getByText(/did not record a detailed reason/)).toBeInTheDocument()
  })
  it('surfaces all failed providers without changing the selected report', () => {
    const one = makeStage({ error: 'Account timed out' }), two = makeStage({ id: 'synthesis_claude', provider: 'Claude', status: 'submission_uncertain', error: 'Submission not confirmed', next_retry_at: null })
    const select = vi.fn()
    render(<ResearchAttentionSummary run={makeRun(one, { stages: [one, two] })} onSelect={select} />)
    expect(screen.getByText('Account timed out')).toBeInTheDocument()
    expect(screen.getByText('Submission not confirmed')).toBeInTheDocument()
    expect(screen.getByText(/No automatic retry is scheduled/)).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'View stage' })[1])
    expect(select).toHaveBeenCalledWith('synthesis_claude')
  })
  it('distinguishes a user pause from provider failure and clears recovered errors', () => {
    const stage = makeStage({ status: 'running', error: 'Old error' })
    render(<><ResearchStopFeedback stage={stage} /><ResearchAttentionSummary run={makeRun(stage, { paused: true })} onSelect={vi.fn()} /></>)
    expect(screen.queryByText('Old error')).not.toBeInTheDocument()
    expect(screen.getByText(/Following steps were paused/)).toBeInTheDocument()
  })
})

describe('Server-backed retry display', () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(now) })

  it.each([1, 5, 30, 90, 250])('shows the correct %i-minute cycle', minutes => {
    const cycle = [1, 5, 30, 90, 250].indexOf(minutes) + 1
    const stage = makeStage({ retry_index: cycle, next_retry_at: new Date(now + minutes * 60_000).toISOString() })
    render(<ResearchRetryPanel run={makeRun(stage)} stage={stage} onRetry={vi.fn()} />)
    expect(screen.getByText(`Retry cycle ${cycle}/5 · ${minutes}-minute interval`)).toBeInTheDocument()
    expect(screen.getByText(/Next: attempt 3/)).toBeInTheDocument()
    expect(screen.getByRole('list').querySelector('[aria-current="step"]')).toHaveTextContent(`${minutes} min`)
  })

  it('ticks locally but never triggers a model call when the deadline passes', () => {
    const stage = makeStage({ next_retry_at: new Date(now + 2000).toISOString() }), onRetry = vi.fn()
    render(<ResearchRetryPanel run={makeRun(stage)} stage={stage} onRetry={onRetry} />)
    expect(screen.getByRole('timer')).toHaveTextContent('00:02')
    act(() => { vi.advanceTimersByTime(1000) })
    expect(screen.getByRole('timer')).toHaveTextContent('00:01')
    act(() => { vi.advanceTimersByTime(4000) })
    expect(screen.getByRole('timer')).toHaveTextContent('00:00')
    expect(screen.getByText('Waiting for the scheduler')).toBeInTheDocument()
    expect(onRetry).not.toHaveBeenCalled()
  })

  it('requires two confirmations for manual retry and disables a pending request', async () => {
    const stage = makeStage(), run = makeRun(stage), onRetry = vi.fn()
    const view = render(<ResearchRetryPanel run={run} stage={stage} onRetry={onRetry} />)
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'I understand, continue' }))
    expect(onRetry).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Yes, Try this stage again' })) })
    expect(onRetry).toHaveBeenCalledTimes(1)
    view.rerender(<ResearchRetryPanel run={run} stage={stage} pending onRetry={onRetry} />)
    expect(screen.getByRole('button', { name: 'Try again' })).toBeDisabled()
  })

  it('hides manual retry even when the run is paused and a sibling is running', () => {
    const stage = makeStage(), sibling = makeStage({ id: 'synthesis_claude', provider: 'Claude', status: 'running' })
    render(<ResearchRetryPanel run={makeRun(stage, { paused: true, status: 'paused', stages: [stage, sibling] })} stage={stage} onRetry={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(screen.getByRole('timer')).toHaveTextContent('—:—')
    expect(screen.queryByRole('button',{name:'Try again'})).not.toBeInTheDocument()
  })

  it('shows the current attempt without a fictional timer while running', () => {
    const stage = makeStage({ status: 'running', next_retry_at: null, retry_index: 0 })
    render(<ResearchRetryPanel run={makeRun(stage, { status: 'running' })} stage={stage} onRetry={vi.fn()} />)
    expect(screen.getByText('Attempt 2 in progress')).toBeInTheDocument()
    expect(screen.queryByRole('timer')).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('distinguishes an unscheduled login problem from an exhausted schedule', () => {
    const stage = makeStage({ status: 'login_required', retry_index: 0, next_retry_at: null })
    const view = render(<ResearchRetryPanel run={makeRun(stage)} stage={stage} onRetry={vi.fn()} />)
    expect(screen.getByText('Review needed before continuing')).toBeInTheDocument()
    expect(screen.queryByText('Automatic retry limit reached')).not.toBeInTheDocument()
    const exhausted = { ...stage, status: 'failed', retry_index: 5 }
    view.rerender(<ResearchRetryPanel run={makeRun(exhausted)} stage={exhausted} onRetry={vi.fn()} />)
    expect(screen.getByText('Automatic retry limit reached')).toBeInTheDocument()
  })

  it('handles legacy missing fields and malformed timestamps without NaN', () => {
    const stage = makeStage({ retry_index: undefined as unknown as number, next_retry_at: 'invalid' })
    expect(retryTiming(stage, now)).toMatchObject({ index: 0, scheduled: false, seconds: 0, progress: 0, exhausted: false })
  })
})

describe('Brief and workflow', () => {
  it('keeps the page compact and shows the entire formatted brief and scope in the modal', async () => {
    render(<ResearchQuestionCard run={makeRun(makeStage())} />)
    expect(screen.queryByText('The final sentence is retained.')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Open the full research brief' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'A long research question' })).toBeInTheDocument()
    expect(within(dialog).getByText('Important evidence').tagName).toBe('STRONG')
    expect(within(dialog).getByText('The final sentence is retained.')).toBeInTheDocument()
    expect(within(dialog).getByText('Primary sources')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('selects the exact stage and labels progress as completed reports', () => {
    const stage = makeStage({ status: 'running' }), onSelect = vi.fn()
    render(<ResearchWorkflow run={makeRun(stage)} selected={stage.id} onSelect={onSelect} />)
    const button = screen.getByRole('button', { name: 'ChatGPT · Independent syntheses · Running' })
    expect(button).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(button)
    expect(onSelect).toHaveBeenCalledWith('synthesis_chatgpt')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
  })
})

describe('Evidence rules',()=>{
  it('shows a blocking reason and its evidence without triggering actions',()=>{
    const policy={version:'research-eca-v1',event:'before_submit',rules_evaluated:14,blocked:true,block_status:'context_limit',factual_verification:false as const,findings:[{id:'ECA-011',severity:'error',action:'block_submission',message:'The full packet exceeds the counted budget.',evidence:{counted_tokens:190000}}]}
    render(<ResearchPolicyPanel policy={policy}/> )
    expect(screen.getByText('Submission blocked · 1')).toBeInTheDocument()
    expect(screen.getByText('The full packet exceeds the counted budget.')).toBeVisible()
    expect(screen.getByText(/not verification that the research claims are true/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it.each(['integrity_error','calibration_required'])('never shows a retry countdown for %s',status=>{
    const stage=makeStage({status,next_retry_at:null,retry_index:0})
    render(<><ResearchStopFeedback stage={stage}/><ResearchRetryPanel run={makeRun(stage)} stage={stage} onRetry={vi.fn()}/></>)
    expect(screen.queryByRole('timer')).not.toBeInTheDocument()
    expect(screen.getByText('Review needed before continuing')).toBeInTheDocument()
  })
})


describe('Common evidence file',()=>{
  it('shows one data hash separately from provider budgets and downloads only on request',()=>{
    const download=vi.fn()
    render(<SharedEvidencePacket packet={{prompt:'task',sha256:'task-hash',estimated_tokens:217397,automatic_input_limit:240000,report_count:5,evidence_packet:{sha256:'f'.repeat(64),bytes:408761,format:'markdown'}}} onDownload={download}/> )
    expect(screen.getByText('Same round, same evidence file')).toBeInTheDocument()
    expect(screen.getByText(/data is not shortened for either model/)).toBeInTheDocument()
    expect(download).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Download common evidence'}))
    expect(download).toHaveBeenCalledOnce()
  })
})
