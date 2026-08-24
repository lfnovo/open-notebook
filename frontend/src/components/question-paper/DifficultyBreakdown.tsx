'use client'

import { useTranslation } from '@/lib/hooks/use-translation'
import type { DifficultyCounts } from '@/lib/types/question-paper'
import { formatQuestionCount } from '@/lib/question-paper-labels'

interface DifficultyBreakdownProps {
  requested?: DifficultyCounts | null
  generated?: DifficultyCounts | null
  remaining?: DifficultyCounts | null
}

function total(mix?: DifficultyCounts | null): number | null {
  if (!mix) return null
  return (mix.easy || 0) + (mix.medium || 0) + (mix.difficult || 0)
}

function MixLines({ mix }: { mix?: DifficultyCounts | null }) {
  if (!mix) return <p className="font-medium">—</p>
  return (
    <ul className="text-sm space-y-0.5">
      <li>Easy: {formatQuestionCount(mix.easy)}</li>
      <li>Medium: {formatQuestionCount(mix.medium)}</li>
      <li>Difficult: {formatQuestionCount(mix.difficult)}</li>
      <li>Total: {formatQuestionCount(total(mix))}</li>
    </ul>
  )
}

export function DifficultyBreakdown({
  requested,
  generated,
  remaining,
}: DifficultyBreakdownProps) {
  const { t } = useTranslation()
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{t.questionPaper.difficultyBreakdown}</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-muted-foreground mb-1">{t.questionPaper.requestedDifficulty}</p>
          <MixLines mix={requested} />
        </div>
        <div>
          <p className="text-muted-foreground mb-1">{t.questionPaper.generatedDifficulty}</p>
          <MixLines mix={generated} />
        </div>
        <div>
          <p className="text-muted-foreground mb-1">{t.questionPaper.remainingDifficulty}</p>
          <MixLines mix={remaining} />
        </div>
      </div>
    </div>
  )
}
