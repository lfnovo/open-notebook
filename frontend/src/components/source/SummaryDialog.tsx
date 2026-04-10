'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { mindmapApi } from '@/lib/api/mindmap'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { FileText, RefreshCw, AlertCircle } from 'lucide-react'

// ── localStorage helpers ──────────────────────────────────────────────────────
const SUMMARY_CACHE_PREFIX = 'summary_cache_'

function loadCachedSummary(sourceId: string): string | null {
  try { return localStorage.getItem(SUMMARY_CACHE_PREFIX + sourceId) } catch { return null }
}
function saveCachedSummary(sourceId: string, summary: string) {
  try { localStorage.setItem(SUMMARY_CACHE_PREFIX + sourceId, summary) } catch {}
}
export function hasSummaryCache(sourceId: string): boolean {
  try { return !!localStorage.getItem(SUMMARY_CACHE_PREFIX + sourceId) } catch { return false }
}

// ── Markdown bold renderer ────────────────────────────────────────────────────
function FormattedText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <span>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <strong key={i} className="font-semibold text-foreground">{p.slice(2, -2)}</strong>
          : <span key={i}>{p}</span>
      )}
    </span>
  )
}

function SummaryContent({ text }: { text: string }) {
  const cleaned = text
    .replace(/^#{1,6}\s+(.+)$/gm, '**$1**')
    .replace(/^-{3,}$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return (
    <div className="space-y-2 text-sm text-foreground leading-relaxed">
      {cleaned.split('\n').map((line, i) => {
        const trimmed = line.trim()
        if (!trimmed) return <div key={i} className="h-1" />
        if (/^[-*]\s/.test(trimmed)) {
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-muted-foreground shrink-0">•</span>
              <span><FormattedText text={trimmed.replace(/^[-*]\s/, '')} /></span>
            </div>
          )
        }
        if (/^\d+\.\s/.test(trimmed)) {
          const num = trimmed.match(/^(\d+)\.\s/)![1]
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-muted-foreground shrink-0 w-5 text-right">{num}.</span>
              <span><FormattedText text={trimmed.replace(/^\d+\.\s/, '')} /></span>
            </div>
          )
        }
        return <p key={i}><FormattedText text={line} /></p>
      })}
    </div>
  )
}

// ── Loading stages ────────────────────────────────────────────────────────────
const LOADING_STAGES = [
  'Connecting to backend...',
  'Fetching source content...',
  'Analysing document with AI (this may take a few minutes)...',
  'Structuring summary...',
  'Almost done...',
]

function useLoadingMessage(loading: boolean) {
  const [idx, setIdx] = useState(0)
  const t = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!loading) { setIdx(0); if (t.current) clearTimeout(t.current); return }
    const delays = [2000, 5000, 15000, 30000]
    const adv = (i: number) => {
      const n = Math.min(i + 1, LOADING_STAGES.length - 1)
      t.current = setTimeout(() => { setIdx(n); if (n < LOADING_STAGES.length - 1) adv(n) }, delays[Math.min(i, delays.length - 1)])
    }
    adv(0)
    return () => { if (t.current) clearTimeout(t.current) }
  }, [loading])
  return LOADING_STAGES[idx]
}

// ── Main dialog ───────────────────────────────────────────────────────────────
interface SummaryDialogProps {
  sourceId: string
  sourceTitle?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SummaryDialog({ sourceId, sourceTitle, open, onOpenChange }: SummaryDialogProps) {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fromCache, setFromCache] = useState(false)
  const loadingMessage = useLoadingMessage(loading)

  const generate = useCallback((forceRegenerate = false) => {
    if (!forceRegenerate) {
      const cached = loadCachedSummary(sourceId)
      if (cached) { setSummary(cached); setError(null); setFromCache(true); return }
    }
    setSummary(null); setError(null); setFromCache(false); setLoading(true)
    mindmapApi.getSourceSummary(sourceId)
      .then(res => {
        setSummary(res.summary)
        saveCachedSummary(sourceId, res.summary)
        setFromCache(false)
      })
      .catch(err => {
        if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
        const detail = err?.response?.data?.detail || err?.message || 'Unknown error'
        setError(detail)
        toast.error('Summary generation failed')
      })
      .finally(() => setLoading(false))
  }, [sourceId])

  useEffect(() => {
    if (!open) return
    generate(false)
  }, [open, sourceId, generate])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Summary{sourceTitle ? ` — ${sourceTitle}` : ''}
            </DialogTitle>
            {!loading && summary && (
              <div className="flex items-center gap-2">
                {fromCache && <span className="text-xs text-muted-foreground">Cached result</span>}
                <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-1.5 h-7 text-xs">
                  <RefreshCw className="h-3 w-3" /> Regenerate
                </Button>
              </div>
            )}
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-1 py-2">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <LoadingSpinner />
              <p className="text-sm text-muted-foreground text-center max-w-xs">{loadingMessage}</p>
              <p className="text-xs text-muted-foreground/60 text-center">AI processing can take several minutes.</p>
            </div>
          )}

          {!loading && error && (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <AlertCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm font-medium text-destructive">Generation failed</p>
              <p className="text-xs text-muted-foreground max-w-sm text-center">{error}</p>
              <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-2">
                <RefreshCw className="h-4 w-4" /> Retry
              </Button>
            </div>
          )}

          {!loading && summary && (
            <div className="rounded-xl border bg-muted/20 p-5">
              <SummaryContent text={summary} />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
