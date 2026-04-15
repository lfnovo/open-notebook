'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import * as d3 from 'd3'
import { mindmapApi, MindMapNode } from '@/lib/api/mindmap'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import {
  AlertCircle, RefreshCw,
  BookOpen, X, ZoomIn, ZoomOut, Maximize2, Network, ImageIcon,
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

// ── JSON extraction helpers ───────────────────────────────────────────────────
function pickNode(parsed: unknown): MindMapNode | null {
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
  const obj = parsed as Record<string, unknown>

  // ── Timeline / event-list schemas ──────────────────────────────────────────

  // Helper: convert an event array into MindMapNode children
  function eventsToChildren(evArr: Record<string, unknown>[]): MindMapNode[] {
    return evArr.map((ev) => {
      const dateRange = [ev.start_date ?? ev.date ?? ev.year, ev.end_date]
        .filter(Boolean).join(' – ')
      const eventText = String(ev.event ?? ev.description ?? ev.title ?? ev.label ?? '')
      const label = dateRange ? `${dateRange}: ${eventText}` : eventText
      return { label: label.trim() }
    })
  }

  // { name, life_events: [...] }
  if (typeof obj.name === 'string' && Array.isArray(obj.life_events)) {
    return { label: obj.name as string, children: eventsToChildren(obj.life_events as Record<string, unknown>[]) }
  }

  // { name, events: [...] }
  if (typeof obj.name === 'string' && Array.isArray(obj.events)) {
    return { label: obj.name as string, children: eventsToChildren(obj.events as Record<string, unknown>[]) }
  }

  // { events: [...] }  — no name at root, infer label from first event or use "Timeline"
  if (!obj.name && Array.isArray(obj.events)) {
    const children = eventsToChildren(obj.events as Record<string, unknown>[])
    const rootLabel = typeof obj.title === 'string' ? obj.title : 'Timeline'
    return { label: rootLabel, children }
  }

  // { life_events: [...] } — no name
  if (!obj.name && Array.isArray(obj.life_events)) {
    const children = eventsToChildren(obj.life_events as Record<string, unknown>[])
    const rootLabel = typeof obj.title === 'string' ? obj.title : 'Timeline'
    return { label: rootLabel, children }
  }

  const rootTitleKey = Object.keys(obj).find(k => k.toLowerCase().replace(/[\s_-]/g, '') === 'roottitle')
  if (rootTitleKey && typeof obj[rootTitleKey] === 'string') {
    const rootLabel = obj[rootTitleKey] as string
    if (typeof obj.label === 'string') {
      const childNode = { ...obj } as unknown as MindMapNode
      return { label: rootLabel, children: [childNode] } as MindMapNode
    }
    return { label: rootLabel, children: (obj.children as MindMapNode[] | undefined) ?? [] } as MindMapNode
  }
  if (typeof obj.label === 'string') return obj as unknown as MindMapNode
  if (typeof obj.root === 'string') {
    return { label: obj.root as string, children: (obj.children as MindMapNode[] | undefined) ?? [] } as MindMapNode
  }
  for (const key of ['mind_map', 'data', 'result', 'mindmap', 'tree', 'node']) {
    const v = obj[key]
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      const inner = v as Record<string, unknown>
      if (typeof inner.label === 'string') return inner as unknown as MindMapNode
      if (typeof inner.root === 'string') {
        return { label: inner.root as string, children: (inner.children as MindMapNode[] | undefined) ?? [] } as MindMapNode
      }
    }
  }

  // ── NEW FALLBACK: Generic arbitrary JSON tree ──────────────────────────────
  // Handles generic structures like {"Subject Name": {"Category": ["Event 1", "Event 2"]}}
  const keys = Object.keys(obj);
  if (keys.length === 1) {
    const rootLabel = keys[0];
    const rootContent = obj[rootLabel];

    const buildTree = (label: string, data: unknown): MindMapNode => {
      if (Array.isArray(data)) {
        return {
          label,
          children: data.map(item => {
            if (typeof item === 'string') return { label: item };
            if (typeof item === 'object' && item !== null) {
              const itemKeys = Object.keys(item);
              if (itemKeys.length === 1) return buildTree(itemKeys[0], (item as any)[itemKeys[0]]);
              return { label: 'Details', children: itemKeys.map(k => buildTree(k, (item as any)[k])) };
            }
            return { label: String(item) };
          }).filter(Boolean) as MindMapNode[]
        };
      }
      if (typeof data === 'object' && data !== null) {
        return {
          label,
          children: Object.entries(data).map(([k, v]) => buildTree(k, v))
        };
      }
      return { label: `${label}: ${data}` };
    };

    if (typeof rootContent === 'object' && rootContent !== null) {
       return buildTree(rootLabel, rootContent);
    }
  }

  return null
}

function extractMindMapJson(raw: unknown): MindMapNode {
  if (raw !== null && typeof raw === 'object' && !Array.isArray(raw)) {
    const node = pickNode(raw)
    if (node) return node
  }
  if (typeof raw !== 'string') throw new Error(`Unsupported content type: ${typeof raw}`)

  // Unescape common escape sequences that LLMs emit
  let text = raw
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")

  // Strip <think> blocks
  text = text.replace(/<think>[\s\S]*?<\/think>/gi, '')

  // FIX: Handle malformed JSON where LLM uses Sets { "string", "string" } instead of Arrays [ "string", "string" ]
  const strPattern = '"(?:\\\\.|[^"\\\\])*"';
  const setPattern = new RegExp(`\\{\\s*(${strPattern}(?:\\s*,\\s*${strPattern})*)\\s*\\}`, 'g');
  text = text.replace(setPattern, '[$1]');

  // Try extracting from a markdown code fence first
  // Using RegExp with `{3}` to avoid markdown formatting conflicts
  const fenceRegex = new RegExp('`{3}(?:json)?\\s*([\\s\\S]*?)\\s*`{3}');
  const fenceMatch = text.match(fenceRegex);
  if (fenceMatch) {
    const fenced = fenceMatch[1].trim()
    try {
      const node = pickNode(JSON.parse(fenced))
      if (node) return node
    } catch {}
  }

  // If the whole string is a JSON-encoded string (starts/ends with quotes), unwrap it
  const tr = text.trim()
  if (tr.startsWith('"') && tr.endsWith('"')) {
    try {
      const inner = JSON.parse(tr)
      if (typeof inner === 'string') text = inner
    } catch {}
  }

  // Try parsing the full text directly
  try {
    const node = pickNode(JSON.parse(text.trim()))
    if (node) return node
  } catch {}

  // Scan for all top-level JSON objects and pick the largest valid one
  const candidates: { node: MindMapNode; len: number }[] = []
  let depth = 0, start = -1, inString = false, escape = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (escape) { escape = false; continue }
    if (ch === '\\' && inString) { escape = true; continue }
    if (ch === '"') { inString = !inString; continue }
    if (inString) continue
    if (ch === '{') { if (depth === 0) start = i; depth++ }
    else if (ch === '}') {
      depth--
      if (depth === 0 && start !== -1) {
        const slice = text.slice(start, i + 1)
        try {
          const node = pickNode(JSON.parse(slice))
          if (node) candidates.push({ node, len: slice.length })
        } catch {}
        start = -1
      }
    }
  }
  if (candidates.length > 0) {
    candidates.sort((a, b) => b.len - a.len)
    return candidates[0].node
  }
  throw new Error(`No valid mind-map JSON found. Content starts with: ${String(raw).slice(0, 300)}`)
}

// ── Markdown renderer ─────────────────────────────────────────────────────────
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
  const cleaned = text.replace(/^#{1,6}\s+(.+)$/gm, '**$1**').replace(/^-{3,}$/gm, '').replace(/\n{3,}/g, '\n\n').trim()
  return (
    <div className="space-y-2 text-sm text-foreground leading-relaxed">
      {cleaned.split('\n').map((line, i) => {
        const t = line.trim()
        if (!t) return <div key={i} className="h-1" />
        if (/^[-*]\s/.test(t)) return (
          <div key={i} className="flex gap-2 pl-2">
            <span className="text-muted-foreground shrink-0">•</span>
            <span><FormattedText text={t.replace(/^[-*]\s/, '')} /></span>
          </div>
        )
        if (/^\d+\.\s/.test(t)) {
          const num = t.match(/^(\d+)\.\s/)![1]
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-muted-foreground shrink-0 w-5 text-right">{num}.</span>
              <span><FormattedText text={t.replace(/^\d+\.\s/, '')} /></span>
            </div>
          )
        }
        return <p key={i}><FormattedText text={line} /></p>
      })}
    </div>
  )
}

// ── Node summary panel ────────────────────────────────────────────────────────
function NodeSummaryPanel({ sourceId, nodeName, context, onClose }: {
  sourceId: string; nodeName: string; context: string; onClose: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fetchSummary = useCallback(() => {
    const cached = loadCachedNodeSummary(sourceId, nodeName, context)
    if (cached) { setSummary(cached); return }
    setLoading(true); setSummary(null); setError(null)
    mindmapApi.getNodeSummary(sourceId, nodeName, context)
      .then(res => { setSummary(res.summary); saveCachedNodeSummary(sourceId, nodeName, context, res.summary) })
      .catch(err => setError(err?.response?.data?.detail || err?.message || 'Unknown error'))
      .finally(() => setLoading(false))
  }, [sourceId, nodeName, context])
  useEffect(() => { fetchSummary() }, [fetchSummary])
  return (
    <div className="flex flex-col h-full border-l border-border/60 bg-muted/20">
      <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-3 border-b border-border/40 shrink-0">
        <div className="flex items-start gap-2 min-w-0">
          <BookOpen className="h-4 w-4 text-indigo-500 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-[11px] text-muted-foreground">Discussing</p>
            <p className="text-sm font-semibold text-foreground truncate">{nodeName}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              in the larger context of <span className="font-medium text-foreground/80">{context}</span>
            </p>
          </div>
        </div>
        <button onClick={onClose} className="shrink-0 rounded-full p-1 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {loading && <div className="flex flex-col items-center justify-center py-10 gap-3"><LoadingSpinner /><p className="text-xs text-muted-foreground text-center">Analysing...</p></div>}
        {!loading && error && <div className="flex flex-col items-center justify-center py-8 gap-2"><AlertCircle className="h-6 w-6 text-destructive" /><p className="text-xs text-destructive">{error}</p><Button variant="outline" size="sm" className="h-7" onClick={fetchSummary}><RefreshCw className="h-3 w-3 mr-1" /> Retry</Button></div>}
        {!loading && summary && <SummaryContent text={summary} />}
      </div>
    </div>
  )
}

// ── D3 Mind Map Component ──────────────────────────────────────────────────────
interface ExtendedHierarchyNode extends d3.HierarchyPointNode<MindMapNode> {
  x0?: number;
  y0?: number;
  id?: string;
  _children?: ExtendedHierarchyNode[] | undefined;
}

function MindMapGraph({ data, onLabelClick, selectedNode, scale, onScaleChange }: { 
  data: MindMapNode; 
  onLabelClick: (label: string, context: string) => void; 
  selectedNode: string | null;
  scale: number;
  onScaleChange?: (scale: number) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null)
  const gRef = useRef<SVGGElement>(null)
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  // Initialize Zoom behavior
  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    const g = d3.select(gRef.current)

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        if (onScaleChange) {
           onScaleChange(event.transform.k)
        }
      })

    zoomBehaviorRef.current = zoom
    svg.call(zoom)
    
    // Initial center (centered on root)
    svg.call(zoom.transform, d3.zoomIdentity.translate(200, 400).scale(scale))
  }, [])

  // Sync scale prop to D3 zoom
  useEffect(() => {
    if (!svgRef.current || !zoomBehaviorRef.current) return
    const svg = d3.select(svgRef.current)
    const currentZoom = d3.zoomTransform(svgRef.current).k
    
    if (Math.abs(currentZoom - scale) > 0.01) {
      svg.transition().duration(300).call(
        zoomBehaviorRef.current.scaleTo,
        scale
      )
    }
  }, [scale])

  // Tree Layout Logic
  useEffect(() => {
    if (!svgRef.current || !data) return

    const g = d3.select(gRef.current)
    const height = 800
    
    // Clear previous elements
    g.selectAll('*').remove()

    const tree = d3.tree<MindMapNode>().nodeSize([120, 320])
    const root = d3.hierarchy(data) as ExtendedHierarchyNode
    root.x0 = height / 2
    root.y0 = 0

    // Initial state: Expand first level only (root + its direct children)
    // Collapse all nodes that are at depth 1 or deeper initially
    root.descendants().forEach(d => {
      if (d.depth >= 1 && d.children) {
        d._children = d.children as ExtendedHierarchyNode[] | undefined
        d.children = undefined
      }
    })

    const update = (source: ExtendedHierarchyNode) => {
      const duration = 750
      const treeData = tree(root)
      const nodes = treeData.descendants() as ExtendedHierarchyNode[]
      const links = treeData.links()

      nodes.forEach(d => { d.y = d.depth * 340 })

      // Links
      const link = g.selectAll<SVGPathElement, d3.HierarchyPointLink<MindMapNode>>('path.link')
        .data(links, (d: any) => d.target.id || (d.target.id = String(Math.random())))

      const linkEnter = link.enter().append('path')
        .attr('class', 'link')
        .attr('d', (d: any) => {
          const o = { x: source.x0 ?? source.x, y: source.y0 ?? source.y }
          return d3.linkHorizontal()({ source: [o.y, o.x], target: [o.y, o.x] } as any)
        })
        .attr('fill', 'none')
        .attr('stroke', '#cbd5e1')
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 0.4)

      link.merge(linkEnter).transition().duration(duration)
        .attr('d', d => d3.linkHorizontal()({ source: [d.source.y, d.source.x], target: [d.target.y, d.target.x] } as any))

      link.exit().transition().duration(duration)
        .attr('d', (d: any) => {
          const o = { x: source.x, y: source.y }
          return d3.linkHorizontal()({ source: [o.y, o.x], target: [o.y, o.x] } as any)
        })
        .remove()

      // Nodes
      const node = g.selectAll<SVGGElement, ExtendedHierarchyNode>('g.node')
        .data(nodes, (d: ExtendedHierarchyNode) => d.id || (d.id = String(Math.random())))

      const nodeEnter = node.enter().append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${source.y0 ?? source.y},${source.x0 ?? source.x})`)

      // Node Anchor Dot
      nodeEnter.filter(d => !!d.children || !!d._children)
        .append('circle')
        .attr('r', 4)
        .attr('fill', '#6366f1')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)

      // ForeignObject for premium React styling
      nodeEnter.append('foreignObject')
        .attr('width', 300)
        .attr('height', 100)
        .attr('x', 0)
        .attr('y', -40)
        .style('overflow', 'visible')
        .append('xhtml:div')
        .attr('class', 'node-container')

      const nodeUpdate = node.merge(nodeEnter)

      // Update the HTML content for ALL nodes (including rotation toggle)
      nodeUpdate.select('foreignObject div.node-container')
        .html((d: ExtendedHierarchyNode) => {
          const isRoot = d.depth === 0
          const hasChildren = !!d.children || !!d._children
          const isSelected = selectedNode === d.data.label
          
          let colorClass = ''
          if (isRoot) colorClass = 'bg-[#e0e7ff] text-[#4338ca] border-[#c7d2fe] ring-4 ring-indigo-50/50 shadow-md font-bold py-3.5 px-8 text-base ring-offset-2'
          else if (hasChildren) colorClass = isSelected 
            ? 'bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe] ring-2 ring-blue-200 shadow-lg font-semibold py-3 px-7 text-sm'
            : 'bg-[#eff6ff] text-[#1e40af] border-[#dbeafe] hover:bg-[#dbeafe] shadow-sm font-semibold py-3 px-7 text-sm'
          else colorClass = isSelected
            ? 'bg-[#d1fae5] text-[#065f46] border-[#a7f3d0] ring-2 ring-emerald-200 shadow-lg font-medium py-2.5 px-6 text-sm'
            : 'bg-[#f0fdf4] text-[#065f46] border-[#d1fae5] hover:bg-[#d1fae5] shadow-sm font-medium py-2.5 px-6 text-sm'

          const rotation = d.children ? 'rotate-90' : ''
          return `
            <div class="flex items-center group relative">
              <div class="node-label border-2 rounded-xl whitespace-nowrap transition-all duration-300 cursor-pointer ${colorClass}">
                 ${d.data.label}
              </div>
              ${hasChildren ? `
                <div class="chevron-toggle ml-[-12px] z-[60] w-6 h-6 rounded-full bg-white border-2 border-indigo-200 flex items-center justify-center shadow-sm hover:scale-110 transition-transform cursor-pointer">
                   <svg class="w-3 h-3 text-indigo-500 transition-transform duration-300 ${rotation}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M9 18l6-6-6-6" /></svg>
                </div>
              ` : ''}
            </div>
          `
        })

      // Attach Handlers
      nodeUpdate.select('.node-label').on('click', (event, d: ExtendedHierarchyNode) => {
        event.stopPropagation()
        onLabelClick(d.data.label, d.parent?.data?.label || '')
      })

      nodeUpdate.select('.chevron-toggle').on('click', (event, d: ExtendedHierarchyNode) => {
        event.stopPropagation()
        if (d.children) {
          d._children = d.children as ExtendedHierarchyNode[] | undefined
          d.children = undefined
        } else if (d._children) {
          d.children = d._children as d3.HierarchyPointNode<MindMapNode>[]
          d._children = undefined
        }
        update(d)
      })

      nodeUpdate.transition().duration(duration)
        .attr('transform', d => `translate(${d.y},${d.x})`)

      node.exit().transition().duration(duration)
        .attr('transform', `translate(${source.y},${source.x})`)
        .remove()

      nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y })
    }

    update(root)

  }, [data, onLabelClick, selectedNode])

  return (
    <div className="w-full h-full relative overflow-hidden bg-[#fcfdfe]">
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 0)', backgroundSize: '40px 40px' }} />
      <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing">
        <g ref={gRef} />
      </svg>
    </div>
  )
}

interface ZoomControlsProps {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onFullscreen?: () => void;
}

function ZoomControls({ scale, onZoomIn, onZoomOut, onReset, onFullscreen }: ZoomControlsProps) {
  return (
    <div className="absolute bottom-3 right-3 flex items-center gap-1 bg-white border border-border/60 rounded-lg px-2 py-1 shadow-sm z-10">
      <button onClick={onZoomOut} className="p-1 rounded hover:bg-slate-100 transition-colors text-slate-500"><ZoomOut className="h-3.5 w-3.5" /></button>
      <span className="text-xs text-slate-500 w-10 text-center">{Math.round(scale * 100)}%</span>
      <button onClick={onZoomIn} className="p-1 rounded hover:bg-slate-100 transition-colors text-slate-500"><ZoomIn className="h-3.5 w-3.5" /></button>
      <div className="w-px h-4 bg-border/60 mx-0.5" />
      <button onClick={onReset} className="p-1 rounded hover:bg-slate-100 transition-colors text-slate-500"><Maximize2 className="h-3.5 w-3.5" /></button>
      {onFullscreen && <><div className="w-px h-4 bg-border/60 mx-0.5" /><button onClick={onFullscreen} className="p-1 rounded hover:bg-slate-100 transition-colors text-slate-500"><Maximize2 className="h-3.5 w-3.5 rotate-45" /></button></>}
    </div>
  )
}

function PhotosTab({ sourceId }: { sourceId: string }) {
  const [images, setImages] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [selectedImg, setSelectedImg] = useState<string | null>(null)
  useEffect(() => {
    if (loaded) return
    setLoading(true)
    mindmapApi.getImages(sourceId).then(res => { setImages(res.images); setLoaded(true) }).catch(() => { setImages([]); setLoaded(true) }).finally(() => setLoading(false))
  }, [sourceId, loaded])
  if (loading) return <div className="flex flex-col items-center justify-center py-16 gap-3"><LoadingSpinner /><p className="text-sm text-muted-foreground">Extracting images...</p></div>
  if (!images.length) return <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground"><ImageIcon className="h-10 w-10 opacity-30" /><p className="text-sm">No images found.</p></div>
  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 p-2">
        {images.map((b64, i) => (
          <button key={i} onClick={() => setSelectedImg(b64)} className="rounded-xl overflow-hidden border border-border/60 hover:border-primary/50 transition-all shadow-sm hover:shadow-md">
            <img src={`data:image/png;base64,${b64}`} alt={`Image ${i + 1}`} className="w-full h-40 object-contain bg-zinc-50 dark:bg-zinc-900" />
          </button>
        ))}
      </div>
      {selectedImg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setSelectedImg(null)}>
          <div className="relative max-w-3xl max-h-[90vh] p-2" onClick={e => e.stopPropagation()}>
            <img src={`data:image/png;base64,${selectedImg}`} alt="Full size" className="max-w-full max-h-[85vh] rounded-xl shadow-2xl object-contain" />
            <button onClick={() => setSelectedImg(null)} className="absolute top-3 right-3 bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-black/80 text-lg">×</button>
          </div>
        </div>
      )}
    </>
  )
}

export interface MindMapInsightViewerProps { content: string; sourceId: string; title?: string | null }
export function isMindMapInsight(insightType: string): boolean { return /mind.?map/i.test(insightType) }

export function MindMapInsightViewer({ content, sourceId, title }: MindMapInsightViewerProps) {
  const [mindMap, setMindMap] = useState<MindMapNode | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [selected, setSelected] = useState<{ nodeName: string, context: string } | null>(null)
  const [scale, setScale] = useState(0.85)
  const [activeTab, setActiveTab] = useState<'graph' | 'photos'>('graph')
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    try {
      const parsed = extractMindMapJson(content)
      setMindMap(parsed)
      saveCache(sourceId, parsed)
      setParseError(null)
    } catch (e) {
      setParseError(e instanceof Error ? e.message : String(e))
      setMindMap(null)
    }
  }, [content, sourceId])

  const rootLabel = mindMap?.label ?? title ?? 'the subject'
  const handleClick = useCallback((nodeName: string, context: string) => {
    setSelected(prev => prev?.nodeName === nodeName && prev?.context === context ? null : { nodeName, context })
  }, [])
  const showPanel = !!selected && activeTab === 'graph' && !!mindMap

  if (parseError) return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-center px-4">
      <AlertCircle className="h-8 w-8 text-destructive" /><p className="text-sm font-medium text-destructive">Could not render mind map</p>
      <p className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">{parseError}</p>
    </div>
  )
  if (!mindMap) return <div className="flex items-center justify-center py-10"><LoadingSpinner /></div>

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex gap-1 border-b border-border/60 shrink-0 mb-2">
        {(['graph', 'photos'] as const).map(tab => (
          <button key={tab} onClick={() => { setActiveTab(tab); if (tab !== 'graph') setSelected(null) }}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
            {tab === 'graph' ? <><Network className="h-3.5 w-3.5" /> Mind Map Graph</> : <><ImageIcon className="h-3.5 w-3.5" /> Photos</>}
          </button>
        ))}
      </div>

      {activeTab === 'graph' && (
        <div className="flex-1 flex overflow-hidden rounded-xl border border-border/60">
          <div className={`relative flex flex-col min-h-0 transition-all duration-300 ${showPanel ? 'w-1/2' : 'w-full'}`}>
             <MindMapGraph 
               data={mindMap} 
               onLabelClick={handleClick} 
               selectedNode={selected?.nodeName ?? null} 
               scale={scale} 
               onScaleChange={setScale}
             />
             <ZoomControls 
               scale={scale} 
               onZoomIn={() => setScale(s => s + 0.15)} 
               onZoomOut={() => setScale(s => s - 0.15)} 
               onReset={() => setScale(0.85)} 
               onFullscreen={() => setFullscreen(true)} 
             />
          </div>
          {showPanel && (
            <div className="w-1/2 flex flex-col min-h-0 overflow-hidden">
              <NodeSummaryPanel sourceId={sourceId} nodeName={selected!.nodeName} context={selected!.context} onClose={() => setSelected(null)} />
            </div>
          )}
        </div>
      )}

      {activeTab === 'photos' && <div className="flex-1 overflow-auto rounded-xl border border-border/60"><PhotosTab sourceId={sourceId} /></div>}

      {fullscreen && (
        <div className="fixed inset-0 z-[100] bg-white flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <span className="text-lg font-bold">{rootLabel} — Knowledge Map</span>
            <button onClick={() => setFullscreen(false)} className="px-4 py-2 rounded-xl bg-slate-100 font-semibold text-sm">Exit Fullscreen</button>
          </div>
          <div className="flex-1 relative">
            <MindMapGraph 
              data={mindMap} 
              onLabelClick={handleClick} 
              selectedNode={selected?.nodeName ?? null} 
              scale={0.8} 
            />
          </div>
        </div>
      )}
    </div>
  )
}