'use client'

import { useRef, useState } from 'react'
import { FileText, Loader2, Upload, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useTranslation } from '@/lib/hooks/use-translation'
import { BRIEF_LIMIT, briefLength, validateBrief } from '../brief-input'
import { BriefDocument, composeBrief, DOCUMENT_ACCEPT, DOCUMENT_COUNT, DOCUMENT_TOTAL_BYTES, readDocument } from '../brief-documents'

export function ResearchBriefInput({question, scope, onQuestion, onScope, busy, onBusy, files, onFiles, accepted, onAccepted, onBlocked}: {
  question: string; scope: string; onQuestion: (text: string) => void; onScope: (text: string) => void
  busy: boolean; onBusy: (value: boolean) => void; files: BriefDocument[]; onFiles: (files: BriefDocument[]) => void
  accepted: boolean; onAccepted: (value: boolean) => void; onBlocked: (value: boolean) => void
}) {
  const {t, language} = useTranslation()
  const input = useRef<HTMLInputElement>(null)
  const reading = useRef(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [progress, setProgress] = useState('')
  const [dragging, setDragging] = useState(false)
  const validFiles = files.filter(file=>!file.error)
  const combined = composeBrief(question,validFiles)
  const issue = question || scope || files.length ? validateBrief(combined, scope) : null
  const structured = validFiles.some(file=>['pdf','docx'].includes(file.kind))
  function error(value: string | null) { setFileError(value); onBlocked(!!value) }
  async function load(selected: File[]) {
    if (!selected.length || busy || reading.current) return
    error(null)
    if (files.length+selected.length>DOCUMENT_COUNT) {error('briefFileCount');return}
    if (files.reduce((sum,file)=>sum+file.size,0)+selected.reduce((sum,file)=>sum+file.size,0)>DOCUMENT_TOTAL_BYTES) {error('briefFilesTotal');return}
    reading.current=true; onBusy(true); onAccepted(false)
    const result = [...files]
    const hashes = new Set(files.filter(file=>!file.error).map(file=>file.sha256))
    for (const file of selected) {
      setProgress(file.name)
      try {
        const document = await readDocument(file)
        if(hashes.has(document.sha256))throw new Error('briefFileDuplicate')
        hashes.add(document.sha256);result.push(document)
      } catch (err) {
        const key = err instanceof Error && /^brief[A-Z]/.test(err.message) ? err.message : 'briefFileReadError'
        result.push({id:crypto.randomUUID(),name:file.name,size:file.size,text:'',sha256:'',kind:'',error:key})
      }
      onFiles([...result])
    }
    reading.current=false; onBusy(false);setProgress('')
    if (input.current) input.current.value = ''
  }
  return <section className="space-y-5 rounded-xl border bg-background/50 p-4 sm:p-5" aria-label={t('research.brief')}>
    <div className="space-y-2"><h3 className="flex items-center gap-2 font-medium"><FileText aria-hidden className="size-5 text-primary"/>{t('research.briefInputTitle')}</h3><p id="brief-input-help" className="max-w-2xl text-base leading-relaxed text-muted-foreground">{t('research.briefInputHelp', {limit: BRIEF_LIMIT.toLocaleString(language)})}</p></div>
    <div onDragOver={event=>{event.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={event=>{event.preventDefault();setDragging(false);void load(Array.from(event.dataTransfer.files))}} className={'space-y-3 rounded-xl border-2 border-dashed p-5 transition-colors '+(dragging?'border-primary bg-primary/10':'border-border bg-muted/20')}>
      <Button type="button" variant="outline" disabled={busy} onClick={()=>input.current?.click()}>{busy ? <Loader2 aria-hidden className="me-2 size-4 animate-spin"/> : <Upload aria-hidden className="me-2 size-4"/>}{t('research.briefFileChoose')}</Button>
      <input ref={input} type="file" accept={DOCUMENT_ACCEPT} multiple className="sr-only" tabIndex={-1} aria-label={t('research.briefFileChoose')} disabled={busy} onChange={event=>void load(Array.from(event.target.files||[]))}/>
      <p className="text-base text-muted-foreground">{t('research.briefFileHelp')}</p>
      <p className="text-base text-muted-foreground">{t('research.briefFilePrivacy')}</p>
      {busy&&<p role="status" className="break-words text-base">{t('research.briefFileReading',{name:progress})}</p>}
    </div>
    {fileError&&<div role="alert" className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-base"><p>{t('research.'+fileError)}</p><Button type="button" variant="outline" onClick={()=>error(null)}>{t('research.briefDiscardSelection')}</Button></div>}
    {files.length>0&&<ul className="space-y-3" aria-label={t('research.briefFileList')}>{files.map(file=><li key={file.id} className={'min-w-0 rounded-xl border p-4 '+(file.error?'border-destructive/40':'border-border')}>
      <div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="break-all font-medium">{file.name}</p><p className="mt-1 text-base text-muted-foreground">{file.error?t('research.briefFileRejected'):t('research.briefFileReady',{characters:briefLength(file.text).toLocaleString(language)})}</p></div><Button type="button" variant="ghost" size="icon" disabled={busy} aria-label={t('research.briefFileRemove',{name:file.name})} onClick={()=>{onFiles(files.filter(item=>item.id!==file.id));onAccepted(false)}}><X aria-hidden className="size-4"/></Button></div>
      {file.error?<p role="alert" className="mt-3 text-base text-destructive">{t('research.'+file.error)}</p>:<details className="mt-3"><summary className="cursor-pointer rounded py-2 text-base focus-visible:outline-2">{t('research.briefFilePreview')}</summary><pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-muted/30 p-3 font-sans text-base leading-relaxed">{file.text}</pre><p className="mt-3 break-all text-base text-muted-foreground">SHA-256: {file.sha256}</p></details>}
    </li>)}</ul>}
    {files.some(file=>file.error)&&<p role="alert" className="text-base text-destructive">{t('research.briefFilesNeedAttention')}</p>}
    {structured&&<label className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-base leading-relaxed"><input type="checkbox" checked={accepted} disabled={busy} onChange={event=>onAccepted(event.target.checked)} className="mt-1 size-4 shrink-0 accent-primary"/><span>{t('research.briefExtractReview')}</span></label>}
    <div className="space-y-2"><Label htmlFor="research-question">{t('research.briefQuestionLabel')}</Label><Textarea id="research-question" value={question} disabled={busy} onChange={event=>onQuestion(event.target.value)} placeholder={t('research.questionPlaceholder')} aria-invalid={!!issue} aria-describedby="brief-input-help brief-input-count brief-input-error" className="min-h-48 text-base leading-relaxed"/></div>
    <div className="space-y-2"><Label htmlFor="research-scope">{t('research.scope')}</Label><Textarea id="research-scope" value={scope} disabled={busy} onChange={event=>onScope(event.target.value)} placeholder={t('research.scopePlaceholder')} aria-invalid={!!issue} aria-describedby="brief-input-error" className="text-base"/></div>
    <p id="brief-input-count" className="text-base tabular-nums text-muted-foreground">{t('research.briefInputCount', {characters:(briefLength(combined)+briefLength(scope)+(briefLength(combined)>12_000&&scope?2:0)).toLocaleString(language),limit:BRIEF_LIMIT.toLocaleString(language)})}</p>
    <div id="brief-input-error" aria-live="polite">{issue&&<p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-base text-destructive">{t('research.'+issue)}</p>}</div>
  </section>
}
