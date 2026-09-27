'use client'
import { AlertCircle, ArrowRight, PauseCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { ResearchRun, ResearchStage } from '../api'
import { attentionStates, roundKeys } from './research-state'

const actions: Record<string, string> = {
  login_required: 'stopLogin', verification_required: 'stopVerification',
  integrity_error: 'stopIntegrity', calibration_required: 'stopCalibration', context_limit: 'stopContext', quota_wait: 'stopQuota',
  research_unavailable: 'stopResearch', browser_changed: 'stopInterface',
  browser_unavailable: 'stopBrowser', submission_uncertain: 'stopUncertain',
}

/** The provider's recorded error is evidence; never invent a timeout root cause. */
export function ResearchStopFeedback({ stage }: { stage: ResearchStage }) {
  const { t } = useTranslation()
  if (!attentionStates.includes(stage.status)) return null
  return <section className="mb-4 space-y-3 rounded-xl border border-amber-500/35 bg-amber-500/5 p-4" aria-label={t('research.stopReason')}>
    <h3 className="flex items-center gap-2 text-sm font-semibold"><AlertCircle aria-hidden className="size-4 text-amber-600 dark:text-amber-400" />{t('research.stopReason')}</h3>
    <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{stage.error?.trim() || t('research.stopUnknown')}</p>
    <p className="text-xs leading-relaxed text-muted-foreground"><span className="font-semibold">{t('research.stopNext')} </span>{t('research.' + (actions[stage.status] || 'stopGeneric'))}</p>
    <p className="text-xs text-muted-foreground">{t('research.stopPreserved')}</p>
  </section>
}

export function ResearchAttentionSummary({ run, onSelect }: { run: ResearchRun; onSelect: (id: string) => void }) {
  const { t } = useTranslation()
  const stages = run.stages.filter(stage => attentionStates.includes(stage.status))
  if (!stages.length && !run.paused && !run.sync_error) return null
  return <section className="space-y-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 sm:p-5" aria-label={t('research.stopSummary')}>
    <h2 className="flex items-center gap-2 text-sm font-semibold"><AlertCircle aria-hidden className="size-4 text-amber-600 dark:text-amber-400" />{t('research.stopSummary')}</h2>
    {run.paused && <p className="flex items-start gap-2 text-sm"><PauseCircle aria-hidden className="mt-0.5 size-4 shrink-0" />{t(run.control_state ? 'research.controlHelp_' + run.control_state : 'research.stopPaused')}</p>}
    {stages.map(stage => <div key={stage.id} className="flex flex-wrap items-start justify-between gap-3 rounded-xl border bg-card p-3">
      <div className="min-w-0 flex-1"><h3 className="text-sm font-medium">{stage.provider} · {t(roundKeys[stage.round])}</h3>
        <p className="mt-1 whitespace-pre-wrap break-words text-sm text-muted-foreground">{stage.error?.trim() || t('research.stopUnknown')}</p>
        <p className="mt-2 text-xs text-muted-foreground">{t(run.paused ? 'research.stopRetryPaused' : stage.next_retry_at ? 'research.stopRetryScheduled' : 'research.stopRetryUnscheduled')}</p>
      </div>
      <Button variant="outline" size="sm" onClick={() => { onSelect(stage.id); requestAnimationFrame(() => document.getElementById('research-stage-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })) }}>{t('research.stopDetails')}<ArrowRight aria-hidden className="ml-2 size-3" /></Button>
    </div>)}
    {run.sync_error && <p className="whitespace-pre-wrap break-words text-sm">{t('research.stopSync')}: {run.sync_error}</p>}
  </section>
}
