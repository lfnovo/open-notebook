'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowLeft, ArrowRight, Check, Loader2, ShieldCheck } from 'lucide-react'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { controlSnapshot, type ControlSnapshot, type ResearchRun } from '../api'
import { roundKeys } from './research-state'

export type ControlAction = 'pause' | 'stop' | 'cancel' | 'resume' | 'restore' | 'retry' | 'automate' | 'skip'
export const actionKey: Record<ControlAction, string> = { pause: 'pause', stop: 'stopNow', cancel: 'abandon', resume: 'resume', restore: 'restore', retry: 'retry', automate: 'automate', skip: 'stageAction_skip' }

export function ResearchActionDialog({ run, action, stageId, onClose, onConfirm }: {
  run: ResearchRun; action: ControlAction; stageId?: string; onClose: () => void; onConfirm: (snapshot: ControlSnapshot) => Promise<unknown>
}) {
  const { t } = useTranslation()
  const [step, setStep] = useState(1)
  const [pending, setPending] = useState(false)
  const [acknowledged, setAcknowledged] = useState(false)
  const [failed, setFailed] = useState(false)
  const [accepted, setAccepted] = useState('')
  const submitting = useRef(false)
  const signature = JSON.stringify([run.id,controlSnapshot(run,stageId)])
  useEffect(() => { setStep(1); setAccepted(''); setAcknowledged(false) }, [signature, action, stageId])
  const restarting = ['resume', 'restore', 'retry', 'automate'].includes(action)
  const affected = run.stages.filter(s => !['completed', 'skipped'].includes(s.status) && (!stageId || s.id === stageId) && (stageId || restarting || s.status === 'running'))
  const browser = affected.some(s => s.mode === 'browser' && s.attempts > 0)
  const account = affected.some(s => s.mode === 'account' && s.attempts > 0)
  const preserved = run.stages.filter(s => s.status === 'completed').length
  const commit = async () => {
    if (!acknowledged || submitting.current || step !== 2 || accepted !== signature) return
    submitting.current = true; setPending(true); setFailed(false)
    try { await onConfirm(controlSnapshot(run,stageId)); onClose() }
    catch { setFailed(true); setStep(1); setAccepted('') }
    finally { submitting.current = false; setPending(false) }
  }
  return <AlertDialog open onOpenChange={open => { if (!open && !pending) onClose() }}>
    <AlertDialogContent className="max-h-[90dvh] overflow-y-auto rounded-2xl sm:max-w-xl" onEscapeKeyDown={event => { if (pending) event.preventDefault() }}>
      <AlertDialogHeader>
        <div className="mb-2 flex items-center justify-between gap-3 text-xs font-medium text-muted-foreground"><span className="flex items-center gap-2"><ShieldCheck aria-hidden className="size-4" />{t('research.safeControl')}</span><span>{t('research.confirmStep', { step, total: 2 })}</span></div>
        <AlertDialogTitle>{t(stageId ? 'research.stageAction_'+action : 'research.' + actionKey[action])}?</AlertDialogTitle>
        <AlertDialogDescription>{t(step === 1 ? 'research.reviewControl' : 'research.finalControlCheck')}</AlertDialogDescription>
      </AlertDialogHeader>
      <div className="space-y-3 text-sm">
        <div className="rounded-xl border bg-muted/30 p-4"><p className="font-semibold">{t('research.controlEffect')}</p><p className="mt-2 leading-relaxed text-muted-foreground">{t('research.'+(stageId?'stageEffect_':'effect_') + action)}</p></div>
        {affected.length > 0 && <div className="rounded-xl border p-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('research.affectedStages')}</p><ul className="space-y-2">{affected.map(s => <li key={s.id} className="flex flex-wrap justify-between gap-2"><span className="font-medium">{s.provider}</span><span className="text-xs text-muted-foreground">{t(roundKeys[s.round])}</span></li>)}</ul></div>}
        {action !== 'skip' && (browser || account && (stageId || action !== 'pause')) && <div className="space-y-2 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-amber-900 dark:text-amber-200"><p className="flex items-center gap-2 font-semibold"><AlertTriangle aria-hidden className="size-4 shrink-0" />{t('research.controlRisks')}</p>{browser && <p className="leading-relaxed">{t('research.browserControlRisk')}</p>}{account && (stageId || action !== 'pause') && <p className="leading-relaxed">{t('research.accountControlRisk')}</p>}</div>}
        <p className="flex items-start gap-2 rounded-xl bg-emerald-500/5 p-3 text-emerald-800 dark:text-emerald-300"><Check aria-hidden className="mt-0.5 size-4 shrink-0" />{t('research.preservedReports', { count: preserved })}</p>
        {step === 2 && <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4 font-medium"><input type="checkbox" className="mt-1 size-4 accent-primary" checked={acknowledged} disabled={pending} onChange={event => setAcknowledged(event.target.checked)} /><span>{t('research.acceptRiskFinal')}</span></label>}
        {failed && <p role="alert" className="text-destructive">{t('research.controlRequestFailed')}</p>}
      </div>
      <AlertDialogFooter>
        {step === 1 ? <AlertDialogCancel disabled={pending}>{t('research.keepResearch')}</AlertDialogCancel> : <Button variant="outline" disabled={pending} onClick={() => { setStep(1); setAcknowledged(false) }}><ArrowLeft aria-hidden className="me-2 size-4" />{t('research.reviewAgain')}</Button>}
        {step === 1 ? <Button onClick={() => { setAccepted(signature); setStep(2) }}>{t('research.acceptControlRisk')}<ArrowRight aria-hidden className="ms-2 size-4" /></Button> : <Button variant={['stop', 'cancel', 'skip'].includes(action) ? 'destructive' : 'default'} disabled={pending || !acknowledged || accepted !== signature} onClick={commit}>{pending ? <Loader2 aria-hidden className="me-2 size-4 animate-spin" /> : <Check aria-hidden className="me-2 size-4" />}{t('research.confirmControl', { action: t(stageId ? 'research.stageAction_'+action : 'research.' + actionKey[action]) })}</Button>}
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
}
