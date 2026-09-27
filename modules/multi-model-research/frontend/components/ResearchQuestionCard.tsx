'use client'

import { FileText, Maximize2, CalendarDays, Download, X } from 'lucide-react'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import { useTranslation } from '@/lib/hooks/use-translation'
import { downloadResearchFile, type ResearchRun } from '@/modules/multi-model-research/api'

// Only the card preview is shortened. The modal and download keep the exact input.
export function briefPreview(text: string) {
  return text.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[`#*_>{}]/g, '').replace(/\s+/g, ' ').trim().slice(0, 260)
}

export function ResearchQuestionCard({ run }: { run: ResearchRun }) {
  const { t, language } = useTranslation()
  return <Dialog>
    <DialogTrigger asChild>
      <button type="button" aria-label={t('research.openBrief')} className="group flex w-full items-start gap-4 rounded-2xl border border-border bg-card p-5 text-start shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/40 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary sm:items-center sm:p-6">
        <span aria-hidden className="relative flex size-14 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-600 dark:text-indigo-300"><FileText className="size-6" /><span className="absolute -bottom-1 -end-1 size-3 rounded-full border-2 border-card bg-indigo-400" /></span>
        <span className="min-w-0 flex-1">
          <span className="mb-2 flex flex-wrap items-center gap-2 text-xs font-medium text-muted-foreground"><span className="uppercase tracking-widest">{t('research.brief')}</span><span className="rounded border px-1.5 py-0.5 text-[10px]">{t('research.markdownDocument')}</span></span>
          <span className="line-clamp-2 break-words text-sm font-medium leading-relaxed sm:text-base">{briefPreview(run.question) || t('research.question')}</span>
          <span className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground"><span>{t('research.characterCount', { characters: run.question.length.toLocaleString(language) })}</span><span className="inline-flex items-center gap-1.5"><CalendarDays aria-hidden className="size-3" />{t('research.asOf')}: {run.as_of || run.created_at.slice(0, 10)}</span></span>
        </span>
        <span className="flex shrink-0 items-center gap-2 rounded-lg border bg-background p-2.5 text-xs font-medium text-foreground transition-colors group-hover:border-primary/40 group-hover:text-primary"><span className="hidden sm:inline">{t('research.readBrief')}</span><Maximize2 aria-hidden className="size-4" /></span>
      </button>
    </DialogTrigger>
    <DialogContent showCloseButton={false} className="flex max-h-[90dvh] w-[calc(100%-1.5rem)] flex-col gap-0 rounded-2xl p-0 motion-reduce:animate-none sm:max-w-4xl">
      <DialogClose asChild><Button variant="ghost" size="icon" className="absolute end-3 top-3 size-11" aria-label={t('common.close')}><X aria-hidden className="size-5" /></Button></DialogClose>
      <DialogHeader className="border-b px-6 py-5 pe-12 text-start sm:px-8 sm:pe-14">
        <DialogTitle className="flex items-center gap-2 text-xl"><FileText aria-hidden className="size-5 text-indigo-500" />{t('research.brief')}</DialogTitle>
        <DialogDescription>{t('research.briefHelp')}</DialogDescription>
      </DialogHeader>
      <div tabIndex={0} role="region" aria-label={t('research.question')} className="min-h-0 overflow-y-auto overscroll-contain px-6 py-6 focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-primary sm:px-10 sm:py-8 [&_code]:!whitespace-pre-wrap [&_code]:break-words">
        <MarkdownRenderer components={{ img: ({ alt }) => <span>{alt}</span>, a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> }}>{run.question}</MarkdownRenderer>
        {run.scope && <section className="mt-8 border-t pt-6"><h3 className="mb-4 text-lg font-semibold">{t('research.scope')}</h3><MarkdownRenderer components={{ img: ({ alt }) => <span>{alt}</span>, a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> }}>{run.scope}</MarkdownRenderer></section>}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t bg-muted/30 px-6 py-3"><p className="text-xs text-muted-foreground">{t('research.fullTextPreserved')}</p><Button variant="outline" size="sm" onClick={() => downloadResearchFile(run.question + (run.scope ? '\n\n' + run.scope : ''), 'research-brief.md')}><Download aria-hidden className="me-2 size-4" />{t('research.downloadBrief')}</Button></div>
    </DialogContent>
  </Dialog>
}
