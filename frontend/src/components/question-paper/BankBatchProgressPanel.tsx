'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  bankBatchElapsedMs,
  bankBatchProgressPercent,
  bankBatchProgressTone,
  bankBatchRemaining,
  formatBankBatchStopReason,
  formatElapsed,
  isBankBatchActive,
  isBankBatchTerminal,
} from '@/lib/question-paper-bank-batch'

const TONE_CLASS: Record<string, string> = {
  pending: 'border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20',
  running: 'border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20',
  completed: 'border-green-300 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20',
  partial: 'border-amber-300 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20',
  failed: 'border-destructive/40 bg-destructive/5',
}

const TONE_TEXT: Record<string, string> = {
  pending: 'text-blue-800 dark:text-blue-200',
  running: 'text-blue-800 dark:text-blue-200',
  completed: 'text-green-800 dark:text-green-200',
  partial: 'text-amber-800 dark:text-amber-200',
  failed: 'text-destructive',
}

export interface BankBatchProgressPanelProps {
  status?: string | null
  requested?: number | null
  accepted?: number | null
  failed?: number | null
  created?: string | null
  errorMessage?: string | null
  stopReason?: string | null
  startedAtMs?: number | null
}

export function BankBatchProgressPanel({
  status,
  requested,
  accepted,
  failed,
  created,
  errorMessage,
  stopReason,
  startedAtMs,
}: BankBatchProgressPanelProps) {
  const { t } = useTranslation()
  const tone = bankBatchProgressTone(status)
  const percent = bankBatchProgressPercent(accepted, requested)
  const remaining = bankBatchRemaining(requested, accepted)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [endedAtMs, setEndedAtMs] = useState<number | null>(null)
  const ticking = isBankBatchActive(status) || tone === 'pending'

  useEffect(() => {
    if (!ticking) return
    const id = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [ticking])

  useEffect(() => {
    if (isBankBatchTerminal(status)) {
      setEndedAtMs((prev) => prev ?? Date.now())
      return
    }
    setEndedAtMs(null)
  }, [status])

  const elapsed = formatElapsed(bankBatchElapsedMs({
    created,
    startedAtMs,
    nowMs,
    endedAtMs,
  }))

  const statusLabel =
    tone === 'completed' ? t.questionPaper.statusCompleted
      : tone === 'partial' ? t.questionPaper.bankStatusPartial
        : tone === 'failed' ? t.questionPaper.statusFailed
          : tone === 'pending' ? t.questionPaper.bankStatusStarting
            : t.questionPaper.statusRunning

  const stopReasonLabel = formatBankBatchStopReason(stopReason)
  const hint =
    tone === 'completed' ? t.questionPaper.bankProgressCompleteHint
      : tone === 'partial'
        ? t.questionPaper.bankProgressPartialHint
            .replace('{accepted}', String(accepted ?? 0))
            .replace('{requested}', String(requested ?? 0))
        : tone === 'failed' ? (errorMessage || t.questionPaper.bankGenerateFailed)
          : t.questionPaper.bankProgressRunningHint

  return (
    <div
      data-testid="bank-batch-progress"
      className={`mt-4 space-y-3 rounded-md border p-4 ${TONE_CLASS[tone]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-sm font-medium flex items-center gap-2 ${TONE_TEXT[tone]}`}>
            {ticking && <Loader2 className="h-4 w-4 animate-spin" />}
            {t.questionPaper.status}: {statusLabel}
          </p>
          <p className={`text-xs mt-1 ${tone === 'failed' ? 'text-destructive' : 'text-muted-foreground'}`}>
            {hint}
          </p>
          {tone === 'partial' && stopReasonLabel ? (
            <p className="text-xs mt-1 text-amber-900 dark:text-amber-200">
              {t.questionPaper.bankStopReason}: {stopReasonLabel}
            </p>
          ) : null}
        </div>
        <p className={`text-2xl font-semibold tabular-nums ${TONE_TEXT[tone]}`}>
          {percent}%
        </p>
      </div>

      <Progress value={percent} />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        <Metric label={t.questionPaper.bankRequested} value={requested ?? '—'} />
        <Metric label={t.questionPaper.bankAccepted} value={accepted ?? 0} />
        <Metric label={t.questionPaper.bankFailedAttempts} value={failed ?? 0} />
        <Metric label={t.questionPaper.bankRemaining} value={remaining} />
        <Metric label={t.questionPaper.bankElapsed} value={elapsed} />
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border bg-background/70 px-2.5 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums mt-0.5">{value}</p>
    </div>
  )
}
