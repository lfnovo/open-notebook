'use client'

import { useState } from 'react'
import { Loader2, Pause, Play, RotateCcw, RotateCw, Square, XCircle, SlidersHorizontal, SkipForward } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useResearchActions } from '../hooks'
import { type ResearchRun, type ResearchStage } from '../api'
import { ResearchActionDialog, type ControlAction } from './ResearchActionDialog'
import { canRetryStage, canSkipStage } from './research-state'

type StageAction = Exclude<ControlAction, 'automate'>
export function ResearchStageControls({ run, stage }: { run: ResearchRun; stage: ResearchStage }) {
  const { t } = useTranslation()
  const { stageAction } = useResearchActions()
  const [intent, setIntent] = useState<StageAction | null>(null)
  if (['completed', 'skipped'].includes(stage.status)) return null
  const held = stage.control_state
  const stopping = held === 'stopping'
  const globalHold = run.paused || !!run.control_state
  const busy = stageAction.isPending || stopping
  const choices: { action: StageAction; icon: typeof Pause; caution?: boolean }[] = []
  if (!held) {
    if (canRetryStage(run, stage)) choices.push({ action: 'retry', icon: RotateCw })
    choices.push({ action: 'pause', icon: Pause })
    if (stage.status === 'running') choices.push({ action: 'stop', icon: Square, caution: true })
    choices.push({ action: 'cancel', icon: XCircle, caution: true })
  } else if (held === 'stop_failed') choices.push({ action: 'stop', icon: Square, caution: true })
  else if (held === 'paused' || held === 'stopped') choices.push({ action: 'resume', icon: Play }, { action: 'cancel', icon: XCircle, caution: true })
  else if (held === 'cancelled') choices.push({ action: 'restore', icon: RotateCcw })
  if (canSkipStage(run, stage)) choices.push({ action: 'skip', icon: SkipForward, caution: true })
  return <section aria-label={t('research.stageControls')} className="mb-5 space-y-3 rounded-xl border border-primary/25 bg-primary/[0.03] p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal aria-hidden className="size-4 text-primary" />{t('research.stageControls')}</h3><span className="text-xs font-medium text-muted-foreground">{stage.provider}</span></div>
    <p className="text-xs leading-relaxed text-muted-foreground">{t('research.stageControlsHelp')}</p>
    {held && <p role="status" className="text-sm font-medium">{t('research.stageState_'+held)}</p>}
    <div className="flex flex-wrap gap-2">{choices.map(({ action, icon: Icon, caution }) => <Button key={action} variant={['resume','restore','retry'].includes(action) ? 'default' : 'outline'} className={'min-h-10 '+(caution ? 'border-red-500/30 text-red-700 dark:text-red-300' : '')} disabled={busy || (globalHold && ['resume','restore','retry'].includes(action))} onClick={() => setIntent(action)}><Icon aria-hidden className="me-2 size-4" />{t('research.stageAction_'+action)}</Button>)}{stopping && <Loader2 aria-label={t('research.stopping')} className="size-5 animate-spin" />}</div>
    {globalHold && <p className="text-xs text-muted-foreground">{t('research.stageGlobalHold')}</p>}
    {stage.control_error && <p role="alert" className="text-sm text-destructive">{stage.control_error}</p>}
    {intent && <ResearchActionDialog run={run} action={intent} stageId={stage.id} onClose={() => setIntent(null)} onConfirm={expectedState => stageAction.mutateAsync({ id: run.id, stage: stage.id, action: intent, expectedState })} />}
  </section>
}
