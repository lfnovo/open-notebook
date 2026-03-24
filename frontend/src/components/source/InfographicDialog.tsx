'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  infographicApi,
  InfographicResponse,
  InfographicColumn,
  InfographicHighlight,
  loadCachedInfographic,
  saveCachedInfographic,
} from '@/lib/api/infographic'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'
import {
  Newspaper, RefreshCw, AlertCircle,
  Info, Calendar, Target, Briefcase, AlertTriangle, Network,
  User, Building, Shield, Activity, BookOpen, BarChart2, MapPin,
  Scale, Lightbulb, FileText, Users, Zap,
} from 'lucide-react'

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

// ── Icon map ──────────────────────────────────────────────────────────────────
const ICON_MAP: Record<string, React.ElementType> = {
  user: User, building: Building, shield: Shield, activity: Activity,
  finance: BarChart2, law: Scale, medical: Zap, briefcase: Briefcase,
  document: FileText, education: BookOpen, chart: BarChart2, network: Network,
  info: Info, calendar: Calendar, target: Target, alert: AlertTriangle,
  lightbulb: Lightbulb, location: MapPin, group: Users, family: Users,
  timeline: Calendar, crime: AlertTriangle,
}

function ColIcon({ name }: { name?: string }) {
  const Icon = ICON_MAP[(name || 'info').toLowerCase()] ?? Info
  return <Icon className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
}

// ── Native React infographic renderer ────────────────────────────────────────
const CARD_COLORS = ['bg-blue-600', 'bg-teal-700', 'bg-slate-600']

function InfographicView({ data }: { data: InfographicResponse }) {
  const header = data.header ?? { title: 'REPORT', subtitle: '' }
  const left = data.left_column ?? []
  const right = data.right_column ?? []
  const highlights = data.highlights ?? []
  const stat = data.stat

  return (
    <div className="rounded-xl border border-border/40 bg-white text-slate-800 p-6 space-y-6">
      {/* Header */}
      <div className="text-center border-b-2 border-blue-700 pb-5">
        <p className="text-xs font-bold tracking-widest text-blue-600 uppercase mb-1">Intelligence Report</p>
        <h2 className="text-2xl font-black uppercase tracking-wide text-slate-900">{header.title}</h2>
        <div className="w-12 h-0.5 bg-blue-600 mx-auto my-2 rounded" />
        {header.subtitle && (
          <p className="text-sm text-slate-500 italic max-w-xl mx-auto leading-relaxed">{header.subtitle}</p>
        )}
      </div>

      {/* Columns */}
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          {left.map((item, i) => <ColBlock key={i} item={item} />)}
        </div>
        <div className="space-y-4">
          {right.map((item, i) => <ColBlock key={i} item={item} />)}
          {stat?.value && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 mt-2">
              <div className="text-3xl font-black text-blue-600 leading-none">{stat.value}</div>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500 mt-1">{stat.label}</div>
            </div>
          )}
        </div>
      </div>

      {/* Highlights */}
      {highlights.length > 0 && (
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Key Highlights &amp; Findings</p>
          <div className="grid grid-cols-3 gap-4">
            {highlights.slice(0, 3).map((h, i) => <HighlightCard key={i} item={h} colorClass={CARD_COLORS[i % CARD_COLORS.length]} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function ColBlock({ item }: { item: InfographicColumn }) {
  return (
    <div className="flex gap-3 items-start">
      <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
        <ColIcon name={item.icon} />
      </div>
      <div>
        <p className="text-[11px] font-extrabold uppercase tracking-wide text-blue-600 mb-0.5">{item.title}</p>
        <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
      </div>
    </div>
  )
}

function HighlightCard({ item, colorClass }: { item: InfographicHighlight; colorClass: string }) {
  return (
    <div className="rounded-lg border border-border/30 overflow-hidden flex flex-col">
      <div className={`${colorClass} text-white px-4 py-3`}>
        <p className="text-xs font-extrabold uppercase tracking-wide leading-tight">{item.title}</p>
        {item.subtitle && <p className="text-[10px] opacity-80 mt-0.5">{item.subtitle}</p>}
      </div>
      <div className="p-3 bg-white flex-1">
        <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
      </div>
    </div>
  )
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
      <DialogContent className="max-w-4xl max-h-[92vh] overflow-y-auto p-0">
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

          {/* Infographic rendered natively */}
          {!loading && data && (data.header || data.left_column || data.highlights) && (
            <InfographicView data={data} />
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
