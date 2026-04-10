'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { mindmapApi, MindMapNode } from '@/lib/api/mindmap'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import {
  GitBranch, ChevronRight, RefreshCw, AlertCircle,
  ImageIcon, Network, BookOpen, X, ZoomIn, ZoomOut, Maximize2,
} from 'lucide-react'

// ── localStorage helpers ──────────────────────────────────────────────────────
const CACHE_PREFIX = 'mindmap_cache_'
const NODE_SUMMARY_PREFIX = 'mindmap_node_summary_'

function loadCached(sourceId: string): MindMapNode | null {
  try { const r = localStorage.getItem(CACHE_PREFIX + sourceId); return r ? JSON.parse(r) : null }
  catch { return null }
}
function saveCache(sourceId: string, node: MindMapNode) {
  try { localStorage.setItem(CACHE_PREFIX + sourceId, JSON.stringify(node)) } catch {}
}
function nodeSummaryKey(sourceId: string, nodeName: string, context: string) {
  const safe = (s: string) => s.toLowerCase().replace(/\s+/g, '_')
  return NODE_SUMMARY_PREFIX + sourceId + '__' + safe(nodeName) + '__ctx__' + safe(context)
}
function loadCachedNodeSummary(sourceId: string, nodeName: string, context: string): string | null {
  try { return localStorage.getItem(nodeSummaryKey(sourceId, nodeName, context)) } catch { return null }
}
function saveCachedNodeSummary(sourceId: string, nodeName: string, context: string, summary: string) {
  try { localStorage.setItem(nodeSummaryKey(sourceId, nodeName, context), summary) } catch {}
}

// ── Robust JSON extractor ─────────────────────────────────────────────────────
/**
 * Extracts a valid MindMapNode JSON object from any LLM output string or object.
 * Handles:
 *   1. Already a plain object (pass-through)
 *   2. Double-encoded JSON string: "{\"label\":...}"
 *   3. Markdown fences: ```json { ... } ```
 *   4. <think>...</think> chain-of-thought noise (qwen3)
 *   5. Prose prefix/suffix around the JSON object
 *   6. Multiple candidate { } blocks — picks the one with a "label" key
 */
function extractMindMapJson(raw: unknown): MindMapNode {
  // Already an object
  if (raw !== null && typeof raw === 'object' && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>
    if (typeof obj.label === 'string') return obj as unknown as MindMapNode
  }

  if (typeof raw !== 'string') {
    throw new Error(`Unsupported content type: ${typeof raw}`)
  }

  let text = raw

  // 1. Strip <think>...</think> blocks (qwen3 chain-of-thought)
  text = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim()

  // 2. Unwrap markdown code fences  ```json ... ```  or  ``` ... ```
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/)
  if (fenceMatch) {
    text = fenceMatch[1].trim()
  }

  // 3. If the whole string is itself JSON-encoded (double-stringified), unwrap it
  if (text.startsWith('"') && text.endsWith('"')) {
    try {
      const inner = JSON.parse(text)
      if (typeof inner === 'string') text = inner
    } catch { /* not double-encoded, keep as-is */ }
  }

  // 4. Try parsing the cleaned text directly
  try {
    const parsed = JSON.parse(text)
    if (parsed && typeof parsed === 'object' && typeof parsed.label === 'string') {
      return parsed as MindMapNode
    }
    // Parsed but no label — maybe it's wrapped: { mind_map: { label: ... } }
    if (parsed?.mind_map?.label) return parsed.mind_map as MindMapNode
  } catch { /* not clean JSON yet — fall through */ }

  // 5. Find ALL { ... } candidates in the raw text, pick the best one
  //    "Best" = contains "label" key and is the largest valid JSON object
  const candidates: MindMapNode[] = []
  let depth = 0
  let start = -1

  for (let i = 0; i < text.length; i++) {
    if (text[i] === '{') {
      if (depth === 0) start = i
      depth++
    } else if (text[i] === '}') {
      depth--
      if (depth === 0 && start !== -1) {
        const slice = text.slice(start, i + 1)
        try {
          const parsed = JSON.parse(slice)
          if (parsed && typeof parsed === 'object' && typeof parsed.label === 'string') {
            candidates.push(parsed as MindMapNode)
          }
        } catch { /* malformed slice, skip */ }
        start = -1
      }
    }
  }

  if (candidates.length > 0) {
    // Pick the candidate with the most children (largest tree)
    candidates.sort((a, b) =>
      JSON.stringify(b).length - JSON.stringify(a).length
    )
    return candidates[0]
  }

  throw new Error(
    `No valid mind-map JSON found. Content preview: ${String(raw).slice(0, 200)}`
  )
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
  // Pre-process: convert ### headers → **bold**, strip --- rules
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
        // Bullet lines starting with - or *
        if (/^[-*]\s/.test(trimmed)) {
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-muted-foreground shrink-0">•</span>
              <span><FormattedText text={trimmed.replace(/^[-*]\s/, '')} /></span>
            </div>
          )
        }
        // Numbered list lines
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

// ── Inline node summary panel ─────────────────────────────────────────────────
// nodeName  = the clicked node
// context   = its parent's label (used as "larger context of {context}")
function NodeSummaryPanel({
  sourceId, nodeName, context, onClose,
}: {
  sourceId: string; nodeName: string; context: string; onClose: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(() => {
    const cached = loadCachedNodeSummary(sourceId, nodeName, context)
    if (cached) { setSummary(cached); return }
    setLoading(true); setSummary(null); setError(null)
    mindmapApi.getNodeSummary(sourceId, nodeName, context)
      .then(res => {
        setSummary(res.summary)
        saveCachedNodeSummary(sourceId, nodeName, context, res.summary)
      })
      .catch(err => setError(err?.response?.data?.detail || err?.message || 'Unknown error'))
      .finally(() => setLoading(false))
  }, [sourceId, nodeName, context])

  useEffect(() => { fetch() }, [fetch])

  return (
    <div className="flex flex-col h-full border-l border-border/60 bg-muted/20">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-3 border-b border-border/40 shrink-0">
        <div className="flex items-start gap-2 min-w-0">
          <BookOpen className="h-4 w-4 text-indigo-500 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-[11px] text-muted-foreground">Discussing</p>
            <p className="text-sm font-semibold text-foreground truncate">{nodeName}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              in the larger context of{' '}
              <span className="font-medium text-foreground/80">{context}</span>
            </p>
          </div>
        </div>
        <button onClick={onClose} className="shrink-0 rounded-full p-1 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {loading && (
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            <LoadingSpinner />
            <p className="text-xs text-muted-foreground text-center">
              Analysing <span className="font-medium">{nodeName}</span>...
            </p>
          </div>
        )}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center py-8 gap-2">
            <AlertCircle className="h-6 w-6 text-destructive" />
            <p className="text-xs text-destructive text-center">{error}</p>
            <Button variant="outline" size="sm" className="text-xs h-7 mt-1" onClick={fetch}>
              <RefreshCw className="h-3 w-3 mr-1" /> Retry
            </Button>
          </div>
        )}
        {!loading && summary && <SummaryContent text={summary} />}
      </div>
    </div>
  )
}

// ── Mind map nodes ────────────────────────────────────────────────────────────
// onLabelClick(nodeName, contextName) — contextName = parent's label
function LeafNode({ label, isSelected, parentLabel, onLabelClick }: {
  label: string; isSelected: boolean; parentLabel: string
  onLabelClick: (label: string, context: string) => void
}) {
  return (
    <div className="flex items-center">
      <div
        onClick={() => onLabelClick(label, parentLabel)}
        className={`px-3 py-1.5 rounded-lg text-xs font-medium border whitespace-nowrap shadow-sm cursor-pointer transition-colors
          ${isSelected
            ? 'bg-teal-500 text-white border-teal-600'
            : 'bg-teal-100 text-teal-800 border-teal-200 hover:bg-teal-200'}`}
      >
        {label}
      </div>
    </div>
  )
}

function BranchNode({ label, expanded, hasChildren, isSelected, isRoot, parentLabel, onToggle, onLabelClick }: {
  label: string; expanded: boolean; hasChildren: boolean
  isSelected: boolean; isRoot: boolean; parentLabel: string
  onToggle: () => void; onLabelClick: (label: string, context: string) => void
}) {
  return (
    <div
      className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium select-none shadow-sm border transition-colors
        ${isRoot
          ? isSelected ? 'bg-indigo-500 text-white border-indigo-600' : 'bg-indigo-100 text-indigo-800 border-indigo-200'
          : isSelected ? 'bg-blue-500 text-white border-blue-600'   : 'bg-blue-100 text-blue-800 border-blue-200'
        }`}
    >
      {/* Label click → open summary (not for root) */}
      <span
        className={`whitespace-nowrap ${!isRoot ? 'cursor-pointer hover:underline underline-offset-2' : ''}`}
        onClick={() => { if (!isRoot) onLabelClick(label, parentLabel) }}
      >
        {label}
      </span>

      {/* Chevron → toggle expand/collapse only */}
      {hasChildren && (
        <span
          onClick={e => { e.stopPropagation(); onToggle() }}
          className={`flex items-center justify-center w-5 h-5 rounded-full bg-white/30 border border-current cursor-pointer transition-transform hover:bg-white/50 ${expanded ? 'rotate-90' : ''}`}
        >
          <ChevronRight className="h-3 w-3" />
        </span>
      )}
    </div>
  )
}

function HorizontalNode({ node, depth = 0, parentLabel, selectedNode, onLabelClick }: {
  node: MindMapNode; depth?: number; parentLabel: string; selectedNode: string | null
  onLabelClick: (label: string, context: string) => void
}) {
  const [expanded, setExpanded] = useState(depth === 0)
  const hasChildren = !!node.children?.length
  const isRoot = depth === 0
  const isSelected = selectedNode === node.label
  const toggle = useCallback(() => setExpanded(e => !e), [])

  if (!hasChildren) return (
    <LeafNode
      label={node.label}
      isSelected={isSelected}
      parentLabel={parentLabel}
      onLabelClick={onLabelClick}
    />
  )

  return (
    <div className="flex items-start gap-0">
      <div className="flex items-center self-center">
        <BranchNode
          label={node.label}
          expanded={expanded}
          hasChildren={hasChildren}
          isSelected={isSelected}
          isRoot={isRoot}
          parentLabel={parentLabel}
          onToggle={toggle}
          onLabelClick={onLabelClick}
        />
      </div>
      {expanded && (
        <div className="flex items-center">
          <div className="w-6 self-stretch flex items-center justify-center" />
          <div className="relative flex flex-col gap-2 pl-2">
            <div className="absolute left-0 top-0 bottom-0 w-px bg-indigo-300" style={{ left: '-1px' }} />
            {node.children!.map((child, i) => (
              <div key={i} className="flex items-center gap-0">
                <div className="w-5 h-px bg-indigo-300 shrink-0" />
                <HorizontalNode
                  node={child}
                  depth={depth + 1}
                  parentLabel={node.label}
                  selectedNode={selectedNode}
                  onLabelClick={onLabelClick}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Zoom controls ─────────────────────────────────────────────────────────────
function ZoomControls({ scale, onZoomIn, onZoomOut, onReset }: {
  scale: number; onZoomIn: () => void; onZoomOut: () => void; onReset: () => void
}) {
  return (
    <div className="absolute bottom-3 right-3 flex items-center gap-1 bg-background/90 border border-border/60 rounded-lg px-2 py-1 shadow-sm z-10">
      <button onClick={onZoomOut} className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground" title="Zoom out">
        <ZoomOut className="h-3.5 w-3.5" />
      </button>
      <span className="text-xs text-muted-foreground w-10 text-center select-none">{Math.round(scale * 100)}%</span>
      <button onClick={onZoomIn} className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground" title="Zoom in">
        <ZoomIn className="h-3.5 w-3.5" />
      </button>
      <div className="w-px h-4 bg-border/60 mx-0.5" />
      <button onClick={onReset} className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground" title="Reset zoom">
        <Maximize2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

// ── Loading stages ────────────────────────────────────────────────────────────
const LOADING_STAGES = [
  'Connecting to backend...', 'Fetching source content...', 'Cleaning and processing text...',
  'Extracting named entities with NLP...', 'Extracting facts with AI (this may take a few minutes)...',
  'Building mind map structure...', 'Almost done...',
]

function useLoadingMessage(loading: boolean) {
  const [idx, setIdx] = useState(0)
  const t = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!loading) { setIdx(0); if (t.current) clearTimeout(t.current); return }
    const delays = [2000, 4000, 8000, 15000, 30000, 60000]
    const adv = (i: number) => {
      const n = Math.min(i + 1, LOADING_STAGES.length - 1)
      t.current = setTimeout(() => { setIdx(n); if (n < LOADING_STAGES.length - 1) adv(n) }, delays[Math.min(i, delays.length - 1)])
    }
    adv(0)
    return () => { if (t.current) clearTimeout(t.current) }
  }, [loading])
  return LOADING_STAGES[idx]
}

// ── Photos tab ────────────────────────────────────────────────────────────────
function PhotosTab({ sourceId }: { sourceId: string }) {
  const [images, setImages] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [selectedImg, setSelectedImg] = useState<string | null>(null)

  useEffect(() => {
    if (loaded) return
    setLoading(true)
    mindmapApi.getImages(sourceId)
      .then(res => { setImages(res.images); setLoaded(true) })
      .catch(() => { setImages([]); setLoaded(true) })
      .finally(() => setLoading(false))
  }, [sourceId, loaded])

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <LoadingSpinner /><p className="text-sm text-muted-foreground">Extracting images from source...</p>
    </div>
  )
  if (images.length === 0) return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
      <ImageIcon className="h-10 w-10 opacity-30" /><p className="text-sm">No images found in this source.</p>
    </div>
  )

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 p-2">
        {images.map((b64, i) => (
          <button key={i} onClick={() => setSelectedImg(b64)}
            className="rounded-xl overflow-hidden border border-border/60 hover:border-primary/50 transition-all shadow-sm hover:shadow-md">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`data:image/png;base64,${b64}`} alt={`Image ${i + 1}`} className="w-full h-40 object-contain bg-zinc-50 dark:bg-zinc-900" />
          </button>
        ))}
      </div>
      {selectedImg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setSelectedImg(null)}>
          <div className="relative max-w-3xl max-h-[90vh] p-2" onClick={e => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`data:image/png;base64,${selectedImg}`} alt="Full size" className="max-w-full max-h-[85vh] rounded-xl shadow-2xl object-contain" />
            <button onClick={() => setSelectedImg(null)} className="absolute top-3 right-3 bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-black/80 text-lg">×</button>
          </div>
        </div>
      )}
    </>
  )
}

// ── Selected node state — stores both node name and its context (parent label) ─
interface SelectedNodeState {
  nodeName: string
  context: string
}

// ── Main dialog ───────────────────────────────────────────────────────────────
interface MindMapDialogProps {
  sourceId: string; sourceTitle?: string | null
  open: boolean; onOpenChange: (open: boolean) => void
}

export function MindMapDialog({ sourceId, sourceTitle, open, onOpenChange }: MindMapDialogProps) {
  const [activeTab, setActiveTab] = useState<'graph' | 'photos'>('graph')
  const [loading, setLoading] = useState(false)
  const [mindMap, setMindMap] = useState<MindMapNode | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fromCache, setFromCache] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const loadingMessage = useLoadingMessage(loading)

  // Selected node: { nodeName, context } — context = parent label
  const [selected, setSelected] = useState<SelectedNodeState | null>(null)
  const [scale, setScale] = useState(1)

  // Root label from the mind map (detected person/topic)
  const rootLabel = mindMap?.label ?? sourceTitle ?? 'the subject'

  const zoomIn  = useCallback(() => setScale(s => Math.min(s + 0.15, 3)), [])
  const zoomOut = useCallback(() => setScale(s => Math.max(s - 0.15, 0.3)), [])
  const zoomReset = useCallback(() => setScale(1), [])

  const generate = useCallback((forceRegenerate = false) => {
    if (!forceRegenerate) {
      const cached = loadCached(sourceId)
      if (cached) {
        try {
          const parsed = extractMindMapJson(cached)
          setMindMap(parsed)
          setError(null)
          setFromCache(true)
          return
        } catch (err) {
          console.warn('[MindMapDialog] Cached data parse error:', err)
          // Fall through to regenerate
        }
      }
    }
    setMindMap(null); setError(null); setFromCache(false); setLoading(true)
    if (abortRef.current) abortRef.current.abort()
    abortRef.current = new AbortController()
    mindmapApi.generate(sourceId)
      .then(r => {
        try {
          const parsed = extractMindMapJson(r.mind_map)
          setMindMap(parsed)
          setFromCache(false)
          saveCache(sourceId, parsed)
          console.log('[MindMapDialog] Generated mind map:', parsed.label)
        } catch (err) {
          const msg = err instanceof Error ? err.message : 'Failed to parse mind map'
          setError(msg)
          toast.error('Mind map parsing failed: ' + msg)
        }
      })
      .catch(err => {
        if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
        const detail = err?.response?.data?.detail || err?.message || 'Unknown error'
        setError(detail); toast.error('Mind map generation failed')
      })
      .finally(() => setLoading(false))
  }, [sourceId])

  useEffect(() => { return () => { if (abortRef.current) abortRef.current.abort() } }, [sourceId])

  useEffect(() => {
    if (!open) return
    setActiveTab('graph'); setSelected(null); setScale(1); generate(false)
  }, [open, sourceId, generate])

  // Called when any node label is clicked
  // nodeName = clicked node, context = its parent's label
  const handleLabelClick = useCallback((nodeName: string, context: string) => {
    setSelected(prev =>
      prev?.nodeName === nodeName && prev?.context === context ? null : { nodeName, context }
    )
  }, [])

  const showPanel = !!selected && activeTab === 'graph' && !!mindMap && !loading

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={`h-[92vh] max-h-[92vh] overflow-hidden flex flex-col transition-all duration-300 ${showPanel ? 'max-w-6xl' : 'max-w-5xl'}`}>
        <DialogHeader className="shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Mind Map{sourceTitle ? ` — ${sourceTitle}` : ''}
            </DialogTitle>
            {!loading && mindMap && (
              <div className="flex items-center gap-2">
                {fromCache && <span className="text-xs text-muted-foreground">Cached result</span>}
                <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-1.5 h-7 text-xs">
                  <RefreshCw className="h-3 w-3" /> Regenerate
                </Button>
              </div>
            )}
          </div>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border/60 shrink-0">
          {(['graph', 'photos'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
                activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab === 'graph'
                ? <><Network className="h-3.5 w-3.5" /> Mind Map Graph</>
                : <><ImageIcon className="h-3.5 w-3.5" /> Photos</>}
            </button>
          ))}
        </div>

        {/* Graph tab */}
        {activeTab === 'graph' && (
          <div className="flex-1 overflow-hidden flex min-h-0">
            {/* Left: graph */}
            <div className={`flex flex-col min-h-0 transition-all duration-300 ${showPanel ? 'w-1/2' : 'w-full'}`}>
              {loading && (
                <div className="flex flex-col items-center justify-center py-16 gap-4 flex-1">
                  <LoadingSpinner />
                  <p className="text-sm text-muted-foreground text-center max-w-xs">{loadingMessage}</p>
                  <p className="text-xs text-muted-foreground/60 text-center">AI processing can take several minutes.</p>
                </div>
              )}
              {!loading && error && (
                <div className="flex flex-col items-center justify-center py-12 gap-4 flex-1">
                  <AlertCircle className="h-10 w-10 text-destructive" />
                  <p className="text-sm font-medium text-destructive">Generation failed</p>
                  <p className="text-xs text-muted-foreground max-w-sm">{error}</p>
                  <Button variant="outline" size="sm" onClick={() => generate(true)} className="gap-2">
                    <RefreshCw className="h-4 w-4" /> Retry
                  </Button>
                </div>
              )}
              {!loading && mindMap && (
                <>
                  <div className="relative flex-1 overflow-auto m-2 rounded-xl border bg-white dark:bg-zinc-950 min-h-[680px]">
                    <div
                      className="flex items-center justify-center p-8 transition-transform duration-150"
                      style={{ transform: `scale(${scale})`, transformOrigin: 'center center', minHeight: '100%' }}
                    >
                      <div className="inline-flex items-start">
                        <HorizontalNode
                          node={mindMap}
                          depth={0}
                          parentLabel={rootLabel}
                          selectedNode={selected?.nodeName ?? null}
                          onLabelClick={handleLabelClick}
                        />
                      </div>
                    </div>
                    <ZoomControls scale={scale} onZoomIn={zoomIn} onZoomOut={zoomOut} onReset={zoomReset} />
                  </div>
                  <p className="text-[11px] text-muted-foreground px-3 pb-2 shrink-0">
                    Click a node label to open summary · Chevron to expand/collapse · Click again to close panel
                  </p>
                </>
              )}
            </div>

            {/* Right: summary panel */}
            {showPanel && (
              <div className="w-1/2 flex flex-col min-h-0 overflow-hidden">
                <NodeSummaryPanel
                  sourceId={sourceId}
                  nodeName={selected!.nodeName}
                  context={selected!.context}
                  onClose={() => setSelected(null)}
                />
              </div>
            )}
          </div>
        )}

        {/* Photos tab */}
        {activeTab === 'photos' && (
          <div className="flex-1 overflow-auto">
            <PhotosTab sourceId={sourceId} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ── Standalone button ─────────────────────────────────────────────────────────
export function MindMapButton({ sourceId, sourceTitle }: { sourceId: string; sourceTitle?: string | null }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <GitBranch className="mr-2 h-4 w-4" /> Mind Map
      </Button>
      <MindMapDialog open={open} onOpenChange={setOpen} sourceId={sourceId} sourceTitle={sourceTitle} />
    </>
  )
}
