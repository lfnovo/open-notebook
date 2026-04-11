'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  infographicApi,
  InfographicResponse,
  loadCachedInfographic,
  saveCachedInfographic,
} from '@/lib/api/infographic'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'
import { Newspaper, RefreshCw, AlertCircle } from 'lucide-react'
import { InfographicInsightViewer } from '@/components/source/InfographicInsightViewer'

// ── Loading stages ────────────────────────────────────────────────────────────
const LOADING_STAGES = [
  'Connecting to backend...',
  'Fetching source content...',
  'Cleaning and processing text...',
  'Analyzing document with AI...',
  'Extracting key facts and building infographic (this may take a few minutes)...',
  'Rendering infographic layout...',
  'Almost done...',
]

function useLoadingMessage(loading: boolean) {
  const [stageIdx, setStageIdx] = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!loading) {
      setStageIdx(0)
      if (timerRef.current) clearTimeout(timerRef.current)
      return
    }
    const delays = [2000, 4000, 8000, 15000, 30000, 60000]
    const advance = (idx: number) => {
      const next = Math.min(idx + 1, LOADING_STAGES.length - 1)
      timerRef.current = setTimeout(() => {
        setStageIdx(next)
        if (next < LOADING_STAGES.length - 1) advance(next)
      }, delays[Math.min(idx, delays.length - 1)])
    }
    advance(0)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [loading])
  return LOADING_STAGES[stageIdx]
}

// ── Dialog ────────────────────────────────────────────────────────────────────
interface InfographicDialogProps {
  sourceId: string
  sourceTitle?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function InfographicDialog({ sourceId, sourceTitle, open, onOpenChange }: InfographicDialogProps) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<InfographicResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fromCache, setFromCache] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  // Track the sourceId that was last loaded so we can detect changes
  const loadedSourceIdRef = useRef<string | null>(null)
  const loadingMessage = useLoadingMessage(loading)

  const generate = useCallback((forceRegenerate = false) => {
    if (!forceRegenerate) {
      const cached = loadCachedInfographic(sourceId)
      // Only use cache if html is actually present
      if (cached && cached.html) {
        setData(cached)
        setError(null)
        setFromCache(true)
        setLoading(false)
        loadedSourceIdRef.current = sourceId
        return
      }
    }

    setData(null)
    setError(null)
    setFromCache(false)
    setLoading(true)
    loadedSourceIdRef.current = sourceId

    if (abortRef.current) abortRef.current.abort()
    abortRef.current = new AbortController()

    infographicApi.generate(sourceId)
      .then(result => {
        setData(result)
        setError(null)
        setFromCache(false)
        saveCachedInfographic(sourceId, result)
      })
      .catch(err => {
        if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
        const detail = err?.response?.data?.detail || err?.message || 'Unknown error'
        setError(detail)
        toast.error('Infographic generation failed')
      })
      .finally(() => setLoading(false))
  }, [sourceId])

  // Abort only when sourceId changes or component unmounts — NOT when dialog closes
  useEffect(() => {
    return () => { if (abortRef.current) abortRef.current.abort() }
  }, [sourceId])

  // Trigger generation when dialog opens or sourceId changes
  useEffect(() => {
    if (!open) return
    // If we already have data for this exact sourceId, don't re-run
    if (loadedSourceIdRef.current === sourceId && data !== null) {
      return
    }
    generate(false)
  }, [open, sourceId]) // intentionally omit `generate` and `data` to avoid loops

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] w-full max-h-[95vh] overflow-y-auto p-0 border-none bg-transparent shadow-none">

        {/* Sticky header */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b px-6 py-4">
          <DialogHeader>
            <div className="flex items-center justify-between gap-2">
              <DialogTitle className="flex items-center gap-2 text-base">
                <Newspaper className="h-5 w-5 text-purple-600" />
                <span>Infographic</span>
                {sourceTitle && (
                  <span className="text-muted-foreground font-normal truncate max-w-[240px]">
                    — {sourceTitle}
                  </span>
                )}
              </DialogTitle>
              {!loading && data && (
                <div className="flex items-center gap-2 shrink-0">
                  {fromCache && (
                    <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-muted">
                      Cached
                    </span>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => generate(true)}
                    className="gap-1.5 h-7 text-xs"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Regenerate
                  </Button>
                </div>
              )}
            </div>
          </DialogHeader>
        </div>

        <div className="px-6 pb-6 pt-4">
          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24 gap-4">
              <LoadingSpinner />
              <p className="text-sm text-muted-foreground text-center max-w-xs">
                {loadingMessage}
              </p>
              <p className="text-xs text-muted-foreground/50 text-center">
                AI processing can take several minutes. Please keep this dialog open.
              </p>
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <AlertCircle className="h-10 w-10 text-destructive" />
              <div className="text-center space-y-1">
                <p className="text-sm font-medium text-destructive">Generation failed</p>
                <p className="text-xs text-muted-foreground max-w-sm">{error}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Retry
              </Button>
            </div>
          )}

          {/* Infographic rendered via InfographicInsightViewer */}
          {!loading && data && (data.header || data.left_column || data.highlights) && (
            <InfographicInsightViewer content={JSON.stringify(data)} />
          )}

          {/* Fallback: no structured data returned */}
          {!loading && data && !data.header && !data.left_column && !data.highlights && !error && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <AlertCircle className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No infographic content was returned. Try regenerating.</p>
              <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-2">
                <RefreshCw className="h-4 w-4" /> Regenerate
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
