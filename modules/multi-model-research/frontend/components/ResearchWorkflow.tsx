'use client'

import { Check, ChevronRight, CircleDot, GitCompareArrows, Layers3, Search, ShieldCheck, SkipForward, Workflow } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { ResearchRun } from '@/modules/multi-model-research/api'
import { cn } from '@/lib/utils'
import { attentionStates, ResearchStatus, roundKeys, statusKeys } from './research-state'

const roundIcons = [Search, Search, GitCompareArrows, Layers3, ShieldCheck]
const providerColor: Record<string, string> = {
  Gemini: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
  ChatGPT: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  Claude: 'bg-orange-500/10 text-orange-700 dark:text-orange-300',
}

export function ResearchWorkflow({ run, selected, onSelect }: { run: ResearchRun; selected: string; onSelect: (id: string) => void }) {
  const { t } = useTranslation()
  const rounds = [...new Set(run.stages.map(s => s.round))]
  const completed = run.stages.filter(s => s.status === 'completed').length
  const skipped = run.stages.filter(s => s.status === 'skipped').length
  const resolved = completed + skipped
  const sources = new Set(run.stages.flatMap(s => s.report?.citations || [])).size
  const activeRound = run.stages.find(s => s.status === 'running')?.round ?? run.stages.find(s => !['completed', 'skipped'].includes(s.status))?.round
  return <section aria-label={t('research.flow')} className="overflow-hidden rounded-2xl border bg-card shadow-sm">
    <div className="border-b bg-muted/20 p-5">
      <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-sm font-semibold"><Workflow aria-hidden className="size-4 text-indigo-500" />{t('research.flow')}</h2><span className="font-mono text-sm text-muted-foreground">{resolved}<span className="text-muted-foreground/60"> / {run.stages.length}</span></span></div>
      <div role="progressbar" aria-label={t('research.progress', { count: resolved })} aria-valuemin={0} aria-valuemax={run.stages.length} aria-valuenow={resolved} className="mt-4 flex h-1.5 gap-1">{run.stages.map(stage => <span key={stage.id} className={cn('flex-1 rounded-full', stage.status === 'completed' ? 'bg-emerald-500' : stage.status === 'skipped' ? 'bg-slate-400' : stage.status === 'running' ? 'bg-blue-500 motion-safe:animate-pulse' : attentionStates.includes(stage.status) ? 'bg-amber-500' : 'bg-muted')} />)}</div>
      <p className="mt-3 text-xs text-muted-foreground">{t('research.evidenceSummary', { reports: completed, sources })}{skipped > 0 && <span className="mt-1 block">{t('research.skippedCount', { count: skipped })}</span>}</p>
    </div>
    <ol className="space-y-0 px-5 py-5">
      {rounds.map((round, phase) => {
        const stages = run.stages.filter(stage => stage.round === round)
        const done = stages.every(stage => ['completed', 'skipped'].includes(stage.status))
        const active = activeRound === round
        const Icon = roundIcons[round]
        return <li key={round} className="relative pb-6 last:pb-0">
          {round < 4 && <span aria-hidden className={cn('absolute start-[15px] top-8 h-[calc(100%-1.5rem)] border-s', done ? 'border-emerald-500/30' : 'border-border')} />}
          <div className="relative mb-3 flex items-center gap-3">
            <span aria-hidden className={cn('flex size-8 shrink-0 items-center justify-center rounded-full border bg-card', done ? 'border-emerald-500/25 text-emerald-600 dark:text-emerald-400' : active ? 'border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-300' : 'text-muted-foreground')}>
              {done ? <Check className="size-4" /> : <Icon className="size-4" />}
            </span>
            <div className="min-w-0 flex-1"><h3 className={cn('text-sm font-semibold', !active && !done && 'text-muted-foreground')}>{t(roundKeys[round])}</h3><p className="mt-0.5 text-[11px] text-muted-foreground">{t('research.phaseNumber', { number: phase + 1, total: rounds.length })}</p></div>
            {active && <span className="rounded-full border border-blue-500/20 bg-blue-500/5 px-2 py-1 text-[10px] font-medium text-blue-700 dark:text-blue-300">{t('research.currentPhase')}</span>}
          </div>
          <div className={cn('ms-11', done ? 'flex flex-wrap gap-2' : 'space-y-2')}>
            {stages.map(stage => <button key={stage.id} type="button" aria-pressed={selected === stage.id} aria-label={`${stage.provider} · ${t(roundKeys[round])} · ${t(statusKeys[stage.status] || 'research.needs_attention')}`} onClick={() => onSelect(stage.id)} className={cn('text-start transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
              done ? 'inline-flex min-h-10 items-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium' : 'block w-full rounded-xl border p-3',
              selected === stage.id ? 'border-primary/60 bg-primary/5 ring-1 ring-primary/10' : stage.status === 'running' ? 'border-blue-500/25 bg-blue-500/5 hover:bg-blue-500/10' : 'border-border bg-background/40 hover:bg-accent/50',
              stage.status === 'pending' && 'text-muted-foreground')}>
              {done ? <>{stage.status === 'skipped' ? <SkipForward aria-hidden className="size-3 text-muted-foreground" /> : <Check aria-hidden className="size-3 text-emerald-500" />}{stage.account_profile === 'preliminary_merge' ? t('research.briefMerge') : stage.provider}{stage.status === 'skipped' && <span className="text-muted-foreground">· {t('research.skipped')}</span>}</> : <>
                <span className="flex items-center gap-2"><span aria-hidden className={cn('flex size-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold', providerColor[stage.provider])}>{stage.provider[0]}</span><span className="flex-1 text-sm font-semibold">{stage.account_profile === 'preliminary_merge' ? t('research.briefMerge') : stage.provider}</span><ChevronRight aria-hidden className="size-3.5 text-muted-foreground" /></span>
                <span className="mt-2 block"><ResearchStatus value={stage.status} /></span>
                {stage.status === 'running' && <span className="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-muted-foreground"><CircleDot aria-hidden className="mt-0.5 size-3 shrink-0 text-blue-500" />{t(stage.account_profile === 'research_review' ? 'research.reviewResearching' : stage.account_profile === 'preliminary_research' ? 'research.agentPreliminary' : stage.mode === 'browser' ? 'research.agentBrowsing' : 'research.agentSynthesizing')}</span>}
              </>}
            </button>)}
          </div>
        </li>
      })}
    </ol>
    <div className="flex items-start gap-2 border-t bg-muted/20 px-5 py-4"><ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" /><p className="text-xs leading-relaxed text-muted-foreground">{t('research.noCut')}</p></div>
  </section>
}
