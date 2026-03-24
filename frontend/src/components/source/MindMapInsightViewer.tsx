'use client'

/**
 * MindMapInsightViewer
 * Renders a mind-map insight (JSON content) with the full interactive
 * graph experience: zoomable tree + node-summary side panel.
 * Reuses all helpers from MindMapDialog.tsx — kept in sync.
 */

import { useState, useEffect, useCallback } from 'react'
import { mindmapApi, MindMapNode } from '@/lib/api/mindmap'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import {
  ChevronRight, AlertCircle, RefreshCw,
  BookOpen, X, ZoomIn, ZoomOut, Maximize2, Network, ImageIcon,
} from 'lucide-react'

// ── localStorage helpers (same keys as MindMapDialog) ────────────────────────
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

// ── Node summary side panel ───────────────────────────────────────────────────
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
        <button
          onClick={onClose}
          className="shrink-0 rounded-full p-1 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
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

// ── Tree nodes ────────────────────────────────────────────────────────────────
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
          : isSelected ? 'bg-blue-500 text-white border-blue-600' : 'bg-blue-100 text-blue-800 border-blue-200'
        }`}
    >
      <span
        className={`whitespace-nowrap ${!isRoot ? 'cursor-pointer hover:underline underline-offset-2' : ''}`}
        onClick={() => { if (!isRoot) onLabelClick(label, parentLabel) }}
      >
        {label}
      </span>
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
    <LeafNode label={node.label} isSelected={isSelected} parentLabel={parentLabel} onLabelClick={onLabelClick} />
  )

  return (
    <div className="flex items-start gap-0">
      <div className="flex items-center self-center">
        <BranchNode
          label={node.label} expanded={expanded} hasChildren={hasChildren}
          isSelected={isSelected} isRoot={isRoot} parentLabel={parentLabel}
          onToggle={toggle} onLabelClick={onLabelClick}
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
                  node={child} depth={depth + 1} parentLabel={node.label}
                  selectedNode={selectedNode} onLabelClick={onLabelClick}
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
      <LoadingSpinner />
      <p className="text-sm text-muted-foreground">Extracting images from source...</p>
    </div>
  )
  if (images.length === 0) return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
      <ImageIcon className="h-10 w-10 opacity-30" />
      <p className="text-sm">No images found in this source.</p>
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

// ── Selected node state ───────────────────────────────────────────────────────
interface SelectedNodeState { nodeName: string; context: string }

// ── Public props ──────────────────────────────────────────────────────────────
export interface MindMapInsightViewerProps {
  /** The raw JSON string stored in insight.content */
  content: string
  /** source_id — needed for node-summary API calls */
  sourceId: string
  /** Optional title shown in the header */
  title?: string | null
}

/**
 * Detects whether an insight_type string represents a mind-map insight.
 * Matches: "mind map", "mindmap", "mind_map", "MIND MAP", etc.
 */
export function isMindMapInsight(insightType: string): boolean {
  return /mind.?map/i.test(insightType)
}

// ── Main viewer ───────────────────────────────────────────────────────────────
export function MindMapInsightViewer({ content, sourceId, title }: MindMapInsightViewerProps) {
  const [mindMap, setMindMap] = useState<MindMapNode | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [selected, setSelected] = useState<SelectedNodeState | null>(null)
  const [scale, setScale] = useState(1)
  const [activeTab, setActiveTab] = useState<'graph' | 'photos'>('graph')

  // Parse JSON content on mount / content change
  useEffect(() => {
    setSelected(null)
    setScale(1)
    try {
      // content may be a JSON string or already an object (edge case)
      const parsed: MindMapNode = typeof content === 'string' ? JSON.parse(content) : content
      if (!parsed?.label) throw new Error('Invalid mind map structure')
      setMindMap(parsed)
      // Also persist to the shared localStorage cache so MindMapDialog reuses it
      saveCache(sourceId, parsed)
      setParseError(null)
    } catch (e) {
      setParseError(e instanceof Error ? e.message : 'Failed to parse mind map data')
      setMindMap(null)
    }
  }, [content, sourceId])

  const rootLabel = mindMap?.label ?? title ?? 'the subject'

  const zoomIn  = useCallback(() => setScale(s => Math.min(s + 0.15, 3)), [])
  const zoomOut = useCallback(() => setScale(s => Math.max(s - 0.15, 0.3)), [])
  const zoomReset = useCallback(() => setScale(1), [])

  const handleLabelClick = useCallback((nodeName: string, context: string) => {
    setSelected(prev =>
      prev?.nodeName === nodeName && prev?.context === context ? null : { nodeName, context }
    )
  }, [])

  const showPanel = !!selected && activeTab === 'graph' && !!mindMap

  if (parseError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm font-medium text-destructive">Could not render mind map</p>
        <p className="text-xs text-muted-foreground max-w-xs">{parseError}</p>
        <details className="mt-2 w-full text-left">
          <summary className="text-xs text-muted-foreground cursor-pointer">Show raw data</summary>
          <pre className="mt-2 text-xs bg-muted rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap break-words">{content}</pre>
        </details>
      </div>
    )
  }

  if (!mindMap) return (
    <div className="flex items-center justify-center py-10">
      <LoadingSpinner />
    </div>
  )

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border/60 shrink-0 mb-2">
        {(['graph', 'photos'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); if (tab !== 'graph') setSelected(null) }}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
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
        <>
          <div className="flex flex-1 min-h-0 overflow-hidden rounded-xl border border-border/60">
            {/* Graph pane */}
            <div className={`relative flex flex-col min-h-0 transition-all duration-300 ${showPanel ? 'w-1/2' : 'w-full'}`}>
              <div className="flex-1 overflow-auto bg-white dark:bg-zinc-950" style={{ minHeight: 320 }}>
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
              </div>
              <ZoomControls scale={scale} onZoomIn={zoomIn} onZoomOut={zoomOut} onReset={zoomReset} />
            </div>

            {/* Node summary panel */}
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
          <p className="text-[11px] text-muted-foreground px-1 pt-1.5 shrink-0">
            Click a node label to open summary · Chevron to expand/collapse · Click again to close panel
          </p>
        </>
      )}

      {/* Photos tab */}
      {activeTab === 'photos' && (
        <div className="flex-1 overflow-auto rounded-xl border border-border/60">
          <PhotosTab sourceId={sourceId} />
        </div>
      )}
    </div>
  )
}
