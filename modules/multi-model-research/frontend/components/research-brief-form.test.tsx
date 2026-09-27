import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ResearchForm } from '../page'
import { researchEn } from '../locales'

const mocks=vi.hoisted(()=>({create:vi.fn(),read:vi.fn()}))
vi.mock('../brief-documents',async importOriginal=>({...await importOriginal<object>(),readDocument:mocks.read}))
vi.mock('@/modules/multi-model-research/hooks',()=>({useResearchActions:()=>({create:{mutateAsync:mocks.create,isPending:false}})}))
vi.mock('./PreliminaryAccounts',()=>({PreliminaryAccounts:()=>null}))
vi.mock('@/lib/hooks/use-translation',()=>({useTranslation:()=>({language:'en-US',t:(key:string,values:Record<string,unknown>={})=>Object.entries(values).reduce((text,[name,value])=>text.replaceAll('{{'+name+'}}',String(value)),researchEn[key.replace('research.','') as keyof typeof researchEn]||key)})}))
afterEach(cleanup)
beforeEach(()=>{mocks.create.mockReset().mockResolvedValue({id:'created'});mocks.read.mockReset().mockImplementation(async(file:File)=>({id:file.name,name:file.name,size:file.size,kind:file.name.split('.').pop(),text:'Complete '+file.name+'\n',sha256:file.name}))})
const start=()=>screen.getByRole('button',{name:researchEn.start})
const picker=()=>screen.getByLabelText('Choose files',{selector:'input'})

describe('Research document form',()=>{
  it('keeps long pasted text and submits every character using accepted API fields',async()=>{
    const done=vi.fn();render(<ResearchForm onCreated={done}/>)
    const input=screen.getByLabelText(researchEn.briefQuestionLabel),text='B'.repeat(39_982)
    expect(input).not.toHaveAttribute('maxlength')
    fireEvent.change(input,{target:{value:text}});fireEvent.click(start())
    await waitFor(()=>expect(done).toHaveBeenCalledWith('created'))
    const {body}=mocks.create.mock.calls[0][0]
    expect(body.question+body.scope).toBe(text)
    expect(body.question.length).toBeLessThanOrEqual(12000)
    expect(body.scope.length).toBeLessThanOrEqual(30000)
  })
  it('starts from multiple mixed files without a typed question',async()=>{
    render(<ResearchForm onCreated={vi.fn()}/>)
    expect(picker()).toHaveAttribute('multiple')
    fireEvent.change(picker(),{target:{files:[new File(['one'],'brief.md'),new File(['two'],'data.csv')]}})
    await waitFor(()=>expect(screen.getByText('data.csv')).toBeInTheDocument())
    expect(start()).toBeEnabled();fireEvent.click(start())
    await waitFor(()=>expect(mocks.create).toHaveBeenCalledOnce())
    const {body}=mocks.create.mock.calls[0][0]
    expect(body.question).toContain('Complete brief.md\n');expect(body.question).toContain('Complete data.csv\n')
  })
  it('blocks submission if any file is rejected; removal explicitly resolves it',async()=>{
    mocks.read.mockRejectedValueOnce(new Error('briefFileBlocked'))
    render(<ResearchForm onCreated={vi.fn()}/>)
    fireEvent.change(screen.getByLabelText(researchEn.briefQuestionLabel),{target:{value:'Investigate this question'}})
    fireEvent.change(picker(),{target:{files:[new File(['x'],'run.exe')]}})
    await waitFor(()=>expect(screen.getByText(researchEn.briefFileBlocked)).toBeInTheDocument())
    expect(start()).toBeDisabled();expect(mocks.create).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Remove run.exe'}));expect(start()).toBeEnabled()
  })
  it('requires review of PDF/DOCX extraction before starting',async()=>{
    render(<ResearchForm onCreated={vi.fn()}/>)
    fireEvent.change(picker(),{target:{files:[new File(['pdf'],'research.pdf')]}})
    await waitFor(()=>expect(screen.getByText('research.pdf')).toBeInTheDocument())
    expect(start()).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox',{name:researchEn.briefExtractReview}));expect(start()).toBeEnabled()
  })
  it('shows overflow without shortening the text or issuing a request',()=>{
    render(<ResearchForm onCreated={vi.fn()}/>)
    const text='x'.repeat(42_001),input=screen.getByLabelText(researchEn.briefQuestionLabel)
    fireEvent.change(input,{target:{value:text}})
    expect(input).toHaveValue(text);expect(start()).toBeDisabled();expect(screen.getByText(researchEn.briefTooLong)).toBeInTheDocument()
    expect(mocks.create).not.toHaveBeenCalled()
  })
  it('does not add an over-count selection or start while reading',async()=>{
    render(<ResearchForm onCreated={vi.fn()}/>)
    fireEvent.change(picker(),{target:{files:Array.from({length:11},(_,i)=>new File(['x'],i+'.md'))}})
    expect(screen.getByText(researchEn.briefFileCount)).toBeInTheDocument();expect(mocks.read).not.toHaveBeenCalled()
    expect(start()).toBeDisabled()
  })
})
