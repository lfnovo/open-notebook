'use client'

import { useEffect, useState } from 'react'
import { Clock3, Loader2, Pause, RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { ResearchRun, ResearchStage, ControlSnapshot } from '@/modules/multi-model-research/api'
import { cn } from '@/lib/utils'
import { ResearchActionDialog } from './ResearchActionDialog'
import { attentionStates, canRetryStage } from './research-state'

// Presentation of workflow.py's schedule. Scheduling belongs exclusively to the server.
export const RETRY_MINUTES = [1, 5, 30, 90, 250] as const

export function retryTiming(stage: ResearchStage, now: number) {
  const index = Number.isInteger(stage.retry_index) ? stage.retry_index : 0
  const due = Date.parse(stage.next_retry_at || '')
  const scheduled = attentionStates.includes(stage.status) && index >= 1 && index <= RETRY_MINUTES.length && Number.isFinite(due)
  const minutes = index >= 1 && index <= RETRY_MINUTES.length ? RETRY_MINUTES[index - 1] : null
  const seconds = scheduled ? Math.max(0, Math.ceil((due - now) / 1000)) : 0
  return { index, due, scheduled, minutes, seconds,
    progress: scheduled && minutes ? Math.min(100, Math.max(0, (1 - seconds / (minutes * 60)) * 100)) : 0,
    exhausted: attentionStates.includes(stage.status) && !scheduled && index >= RETRY_MINUTES.length }
}

export function countdownText(seconds: number) {
  const hh = Math.floor(seconds / 3600), mm = Math.floor(seconds % 3600 / 60), ss = seconds % 60
  return (hh ? [hh, mm, ss] : [mm, ss]).map(value => String(value).padStart(2, '0')).join(':')
}

export function ResearchRetryPanel({ run, stage, onRetry, pending = false, showAction = true }: {
  run: ResearchRun; stage: ResearchStage; onRetry: (snapshot: ControlSnapshot) => void | Promise<unknown>; pending?: boolean; showAction?: boolean
}) {
  const { t, language } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const [now, setNow] = useState(0)
  useEffect(() => {
    setNow(Date.now())
    if (!stage.next_retry_at || run.paused) return
    const interval = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [stage.next_retry_at, run.paused])
  if (stage.mode === 'import' || (!attentionStates.includes(stage.status) && stage.status !== 'running')) return null

  const timing = retryTiming(stage, now)
  const running = stage.status === 'running'
  const busy = stage.status === 'running'
  const attempts = stage.attempts || 0
  const eligible = canRetryStage(run, stage)
  const modeKey = running ? 'research.attemptInProgress' : run.paused ? 'research.retryPaused' : timing.scheduled ? (timing.seconds > 0 || !now ? 'research.retryCountdown' : 'research.retryDue') : timing.exhausted ? 'research.retryFinished' : 'research.retryNeedsAction'

  return <section aria-label={t('research.retryStatus')} className={cn('mb-5 overflow-hidden rounded-xl border', running ? 'border-blue-500/20 bg-blue-500/5' : 'border-amber-500/25 bg-amber-500/5')}>
    <div className="flex flex-wrap items-center justify-between gap-4 p-4">
      <div className="min-w-[170px] flex-1">
        <p className="flex items-center gap-2 text-sm font-semibold">{running ? <Loader2 aria-hidden className="size-4 text-blue-500 motion-safe:animate-spin" /> : run.paused ? <Pause aria-hidden className="size-4" /> : <Clock3 aria-hidden className="size-4 text-amber-600 dark:text-amber-300" />}{t(modeKey)}</p>
        <p className="mt-1.5 text-xs text-muted-foreground">{t(running ? 'research.currentAttempt' : 'research.attemptsSoFar', { count: attempts })}{timing.scheduled && <> · {t('research.nextAttempt', { count: attempts + 1 })}</>}</p>
        {timing.minutes && (timing.scheduled || running) && <p className="mt-1 text-xs font-medium">{t('research.retryCycle', { cycle: timing.index, total: RETRY_MINUTES.length, minutes: timing.minutes })}</p>}
      </div>
      {timing.scheduled && <div className="min-w-0 text-start sm:text-end"><div role="timer" aria-live="off" aria-label={t('research.timeUntilRetry')} className="font-mono text-3xl font-medium tabular-nums tracking-tight text-amber-800 dark:text-amber-200">{run.paused || !now ? '—:—' : countdownText(timing.seconds)}</div><p className="mt-1 text-[11px] text-muted-foreground">{run.paused ? t('research.retryPaused') : t('research.autoRetryAt', { time: new Date(timing.due).toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' }) })}</p></div>}
    </div>
    {!running && <div className="border-t border-amber-500/15 px-4 pb-4 pt-3">
      <ol aria-label={t('research.retryScheduleLabel')} title={t('research.autoRetrySchedule')} className="grid grid-cols-5 gap-1.5">
        {RETRY_MINUTES.map((minutes, i) => <li key={minutes} aria-current={timing.scheduled && timing.index === i + 1 ? 'step' : undefined} className={cn('min-w-0 rounded-lg border px-1 py-2 text-center', timing.scheduled && timing.index === i + 1 ? 'border-amber-500/50 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-transparent bg-muted/60 text-muted-foreground')}>
          <span className="block text-[10px] opacity-80">{i + 1}/{RETRY_MINUTES.length}</span><span className="mt-0.5 block whitespace-nowrap text-[10px] font-semibold sm:text-xs">{t('research.retryMinutes', { minutes })}</span>
        </li>)}
      </ol>
      {timing.scheduled && !run.paused && <div role="progressbar" aria-label={t('research.retryWaitProgress')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(timing.progress)} className="mt-3 h-1 overflow-hidden rounded-full bg-amber-500/10"><div className="h-full rounded-full bg-amber-500" style={{ width: `${now ? timing.progress : 0}%` }} /></div>}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="min-w-[160px] flex-1 text-xs leading-relaxed text-muted-foreground">{t(busy ? 'research.retryAfterActive' : run.paused ? 'research.retryPausedHelp' : timing.scheduled ? 'research.retryCountdownHelp' : timing.exhausted ? 'research.autoRetryExhausted' : 'research.retryActionHelp')}</p>
        {showAction && eligible && <Button size="sm" variant="outline" disabled={pending} className="min-h-10 border-amber-500/40 bg-background" title={t(run.paused ? 'research.retryResumesRun' : 'research.retryHelp')} onClick={() => setConfirming(true)}>{pending ? <Loader2 aria-hidden className="me-2 size-4 motion-safe:animate-spin" /> : <RotateCw aria-hidden className="me-2 size-4" />}{t('research.retry')}</Button>}
      </div>
    </div>}
    {confirming && eligible && <ResearchActionDialog run={run} action="retry" stageId={stage.id} onClose={() => setConfirming(false)} onConfirm={async snapshot => onRetry(snapshot)} />}
  </section>
}
