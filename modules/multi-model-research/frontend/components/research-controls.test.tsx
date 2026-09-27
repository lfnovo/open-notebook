import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ResearchRun } from '../api'
import { researchEn } from '../locales'
import { ResearchStageControls } from './ResearchStageControls'
import { ResearchControls } from './ResearchControls'
import { ResearchActionDialog } from './ResearchActionDialog'
import { ResearchWorkflow } from './ResearchWorkflow'

const mutation = vi.hoisted(() => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}), isPending: false }))
vi.mock('../hooks', () => ({ useResearchActions: () => ({ action: mutation, stageAction: mutation, error: vi.fn() }) }))
vi.mock('@/lib/hooks/use-translation', () => ({ useTranslation: () => ({ t: (key: string, params: Record<string, unknown> = {}) => Object.entries(params).reduce((s, [k, v]) => s.replaceAll('{{' + k + '}}', String(v)), researchEn[key.replace('research.', '') as keyof typeof researchEn] || key) }) }))
const run: ResearchRun = { id: 'test', question: 'Question', scope: '', as_of: '', language: 'English', auto_synthesize: true, execution_mode: 'browser', paused: false, status: 'running', created_at: '', updated_at: '', notebook_id: null, sync_error: null, stages: [
  { id: 'pre_research_claude', provider: 'Claude', round: 0, mode: 'account', status: 'running', attempts: 1, report: null, error: null, usage: null, note_id: null, browser_progress: null, retry_index: 0, next_retry_at: null },
] }
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('Research control protection', () => {
  it('offers distinct pause, immediate stop and end controls while running; does not submit on first click', async () => {
    render(<ResearchControls run={run} />)
    expect(screen.getByRole('button', { name: 'Pause after current steps' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'End research' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Continue research' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stop now' }))
    expect(screen.getByRole('alertdialog')).toBeVisible()
    expect(mutation.mutateAsync).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'I understand, continue' }))
    expect(mutation.mutateAsync).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Yes, Stop now' })) })
    expect(mutation.mutateAsync).toHaveBeenCalledExactlyOnceWith({ id: 'test', action: 'stop', expectedState: {status:'running',paused:false,control_state:null,stages:[['pre_research_claude','running',1,null]]} })
  })
  it('dismisses a review without making any mutation', () => {
    render(<ResearchControls run={run} />)
    fireEvent.click(screen.getByRole('button', { name: 'End research' }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep current state' }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(mutation.mutateAsync).not.toHaveBeenCalled()
  })
  it('invalidates an accepted risk if polling changes an affected stage', () => {
    const view = render(<ResearchActionDialog run={run} action="stop" onClose={vi.fn()} onConfirm={mutation.mutateAsync} />)
    fireEvent.click(screen.getByRole('button', { name: 'I understand, continue' }))
    view.rerender(<ResearchActionDialog run={{ ...run, stages: [{ ...run.stages[0], status: 'completed' }] }} action="stop" onClose={vi.fn()} onConfirm={mutation.mutateAsync} />)
    expect(screen.queryByRole('button', { name: 'Yes, Stop now' })).not.toBeInTheDocument()
    expect(mutation.mutateAsync).not.toHaveBeenCalled()
  })
  it('explains web reconnection without promising remote cancellation', () => {
    render(<ResearchActionDialog run={{ ...run, stages: [{ ...run.stages[0], mode: 'browser' }] }} action="resume" onClose={vi.fn()} onConfirm={vi.fn()} />)
    expect(screen.getByText(/not a verified cancellation at the provider/)).toBeVisible()
    expect(screen.getByText(/uncertain submission is not blindly resent/)).toBeVisible()
  })
  it('locks further controls while stopping, and offers explicit restore only for an ended run', () => {
    const view = render(<ResearchControls run={{ ...run, paused: true, control_state: 'stopping', status: 'stopping' }} />)
    expect(screen.getByRole('button', { name: 'Stopping…' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Continue research' })).not.toBeInTheDocument()
    view.rerender(<ResearchControls run={{ ...run, paused: true, control_state: 'cancelled', status: 'cancelled', stages: [{ ...run.stages[0], status: 'interrupted' }] }} />)
    expect(screen.getByRole('button', { name: 'Restore and continue' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Continue research' })).not.toBeInTheDocument()
  })
  it('guards double clicks during the final request', async () => {
    let resolve!: () => void
    const confirm = vi.fn(() => new Promise<void>(r => { resolve = r }))
    render(<ResearchActionDialog run={run} action="stop" onClose={vi.fn()} onConfirm={confirm} />)
    fireEvent.click(screen.getByRole('button', { name: 'I understand, continue' }))
    const button = screen.getByRole('button', { name: 'Yes, Stop now' })
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(button); fireEvent.click(button)
    expect(confirm).toHaveBeenCalledOnce(); expect(button).toBeDisabled()
    await act(async () => resolve())
  })
})

it('offers target retry while a sibling runs and submits only the selected stage after two steps', async () => {
  const stage={...run.stages[0],id:'research_chatgpt',provider:'ChatGPT',status:'quota_wait'}
  const data={...run,stages:[...run.stages,stage]}
  render(<ResearchStageControls run={data} stage={stage} />)
  fireEvent.click(screen.getByRole('button',{name:'Try this stage again'}))
  expect(mutation.mutateAsync).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'I understand, continue'}))
  fireEvent.click(screen.getByRole('checkbox'))
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Yes, Try this stage again'}))})
  expect(mutation.mutateAsync).toHaveBeenCalledExactlyOnceWith({id:'test',stage:'research_chatgpt',action:'retry',expectedState:{scope:'stage',run_paused:false,run_control_state:null,stage:['research_chatgpt','quota_wait',1,null]}})
})
it('keeps resume disabled during a whole-run pause', () => {
  const stage={...run.stages[0],status:'stopped',control_state:'stopped' as const}
  render(<ResearchStageControls run={{...run,paused:true,stages:[stage]}} stage={stage} />)
  expect(screen.getByRole('button',{name:'Resume stage'})).toBeDisabled()
})

const savedReport = { content: 'Original research', researched_at: null, sha256: 'report-hash', citations: ['https://example.org'], provenance: 'account_preliminary_research', origin_url: '', evidence: [], original_files: [] }
it('requires two confirmations before skipping a quota-blocked contribution', async () => {
  const stage = { ...run.stages[0], id: 'pre_research_gemini', provider: 'Gemini', status: 'quota_wait' }
  const data = { ...run, stages: [stage, { ...run.stages[0], status: 'completed', report: savedReport }] }
  render(<ResearchStageControls run={data} stage={stage} />)
  fireEvent.click(screen.getByRole('button', { name: 'Skip this stage' }))
  expect(screen.getByText(/This provider contributes no report or verification/)).toBeVisible()
  expect(mutation.mutateAsync).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'I understand, continue' }))
  expect(screen.getByRole('button', { name: 'Yes, Skip this stage' })).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Yes, Skip this stage' })) })
  expect(mutation.mutateAsync).toHaveBeenCalledExactlyOnceWith({ id: 'test', stage: stage.id, action: 'skip', expectedState: { scope: 'stage', run_paused: false, run_control_state: null, stage: [stage.id, 'quota_wait', 1, null] } })
})

it('does not offer skip for running, already skipped or sole contributions', () => {
  const view = render(<ResearchStageControls run={run} stage={run.stages[0]} />)
  expect(screen.queryByRole('button', { name: 'Skip this stage' })).not.toBeInTheDocument()
  const stage = { ...run.stages[0], status: 'skipped' }
  view.rerender(<ResearchStageControls run={{ ...run, stages: [stage] }} stage={stage} />)
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it('shows skipped work separately from saved reports and selects the next phase', () => {
  const data = { ...run, stages: [
    { ...run.stages[0], id: 'pre_research_gemini', provider: 'Gemini', status: 'skipped' },
    { ...run.stages[0], status: 'completed', report: savedReport },
    { ...run.stages[0], id: 'research_claude', round: 1, status: 'waiting_input' },
  ] }
  render(<ResearchWorkflow run={data} selected="research_claude" onSelect={vi.fn()} />)
  expect(screen.getByText('1 skipped · no report counted')).toBeVisible()
  expect(screen.getByText(/1 reports saved/)).toBeVisible()
  expect(screen.getByRole('button', { name: /Gemini.*Skipped/ })).toBeVisible()
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2')
})
