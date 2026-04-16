'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d'
import { AppShell } from '@/components/layout/AppShell'
import { sourcesApi } from '@/lib/api/sources'
import { CommonGraphResponse, SourceListResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useModels, useModelDefaults } from '@/lib/hooks/use-models'
import type { AxiosError } from 'axios'

const DEFAULT_PROMPT = `You are an expert investigative analyst. Analyze the documents below and extract a person-activity network.

IMPORTANT: Return ONLY valid JSON. No explanation, no text before or after.

Required JSON format:
{
  "persons": [
    {"id": "p1", "name": "Full Name", "doc_indices": [0]}
  ],
  "activities": [
    {"id": "a1", "label": "activity description", "persons": ["p1"]}
  ],
  "connections": [
    {"from": "p1", "to": "p2", "label": "relationship"}
  ]
}

Instructions:
1. persons: Every named individual. doc_indices = list of document numbers (0-based) where they appear.
2. activities: Key events, crimes, locations, meetings, transactions. persons = IDs of people involved.
3. connections: Only direct person-to-person relationships explicitly stated in the text.
4. Use short labels (max 5 words).
5. Start your response with { and end with }`

const NODE_COLORS = {
  source: '#6366f1',
  person: '#0ea5e9',
  activity: '#f59e0b',
}

const NODE_TEXT_COLORS = {
  source: '#ffffff',
  person: '#ffffff',
  activity: '#1c1917',
}

const LINK_COLORS: Record<string, string> = {
  appears_in: 'rgba(99,102,241,0.35)',
  involved_in: 'rgba(245,158,11,0.55)',
  connection: 'rgba(239,68,68,0.75)',
  default: 'rgba(180,180,180,0.3)',
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

function getNodeDims(node: any): { w: number; h: number; r: number; fontSize: number } {
  const type = node.type || 'activity'
  const label = node.label || ''
  const fontSize = type === 'person' ? 12 : type === 'source' ? 11 : 10
  const charW = fontSize * 0.62
  const textW = Math.min(label.length, 18) * charW
  const padX = type === 'person' ? 18 : 14
  const padY = type === 'person' ? 10 : 8
  const w = Math.max(textW + padX * 2, type === 'person' ? 80 : 60)
  const h = fontSize + padY * 2
  const r = h / 2
  return { w, h, r, fontSize }
}

type GraphNode = {
  id: string
  label: string
  type: 'source' | 'person' | 'activity'
  initials?: string
  weight?: number
  x?: number
  y?: number
}

type GraphLink = {
  source: string | GraphNode
  target: string | GraphNode
  type?: string
  label?: string
  weight?: number
}

type GraphData = { nodes: GraphNode[]; links: GraphLink[] }

function getNodeId(n: string | GraphNode): string {
  return typeof n === 'string' ? n : n.id
}

function NetworkGraphViewer({ graph, sourceCount }: { graph: GraphData; sourceCount: number }) {
  const graphRef = useRef<ForceGraphMethods | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 560 })
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const connectedNodeIds = useMemo(() => {
    if (!hoverNode) return new Set<string>()
    const ids = new Set<string>()
    graph.links.forEach((l) => {
      const s = getNodeId(l.source), t = getNodeId(l.target)
      if (s === hoverNode.id) ids.add(t)
      if (t === hoverNode.id) ids.add(s)
    })
    return ids
  }, [graph.links, hoverNode])

  const hoveredLinkSet = useMemo(() => {
    if (!hoverNode) return new Set<string>()
    return new Set(graph.links.filter((l) => getNodeId(l.source) === hoverNode.id || getNodeId(l.target) === hoverNode.id).map((l) => `${getNodeId(l.source)}--${getNodeId(l.target)}`))
  }, [graph.links, hoverNode])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((e) => {
      const r = e[0].contentRect
      setDimensions({ width: Math.max(500, Math.round(r.width)), height: Math.max(480, Math.round(r.height)) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const fg = graphRef.current
    if (!fg) return
    fg.d3Force('charge')?.strength(-500)
    fg.d3Force('link')?.distance((l: any) => l.type === 'connection' ? 180 : l.type === 'involved_in' ? 140 : 110)
  }, [dimensions])

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const isHovered = hoverNode?.id === node.id
    const isConnected = connectedNodeIds.has(node.id)
    const dimmed = hoverNode && !isHovered && !isConnected
    const type = node.type || 'activity'
    const color = NODE_COLORS[type as keyof typeof NODE_COLORS] || '#888'
    const textColor = NODE_TEXT_COLORS[type as keyof typeof NODE_TEXT_COLORS] || '#fff'
    const { w, h, r, fontSize } = getNodeDims(node)
    const x = node.x - w / 2
    const y = node.y - h / 2

    ctx.globalAlpha = dimmed ? 0.1 : 1
    if (isHovered) { ctx.shadowColor = color; ctx.shadowBlur = 20 }

    roundRect(ctx, x, y, w, h, r)
    ctx.fillStyle = color
    ctx.fill()

    roundRect(ctx, x, y, w, h, r)
    ctx.strokeStyle = isHovered ? '#ffffff' : 'rgba(255,255,255,0.25)'
    ctx.lineWidth = isHovered ? 2.5 : 1
    ctx.stroke()
    ctx.shadowBlur = 0

    const lbl = (node.label || '').length > 18 ? node.label.slice(0, 16) + '…' : node.label
    ctx.fillStyle = textColor
    ctx.font = `${type === 'person' ? 'bold ' : ''}${fontSize}px Sans-Serif`
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(lbl, node.x, node.y)
    ctx.globalAlpha = 1
  }, [hoverNode, connectedNodeIds])

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const s = link.source, t = link.target
    if (!s?.x || !t?.x) return
    const key = `${getNodeId(s)}--${getNodeId(t)}`
    const isHighlighted = hoveredLinkSet.has(key)
    const dimmed = hoverNode && !isHighlighted
    const ltype = link.type || 'default'
    ctx.globalAlpha = dimmed ? 0.04 : 1
    ctx.strokeStyle = isHighlighted ? (ltype === 'connection' ? 'rgba(239,68,68,0.95)' : ltype === 'involved_in' ? 'rgba(245,158,11,0.95)' : 'rgba(99,102,241,0.8)') : (LINK_COLORS[ltype] || LINK_COLORS.default)
    ctx.lineWidth = ltype === 'connection' ? (isHighlighted ? 3 : 2) : (isHighlighted ? 2 : 1)
    if (ltype === 'connection') ctx.setLineDash([6, 3]); else ctx.setLineDash([])
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke()
    ctx.setLineDash([])
    if (isHighlighted && link.label) {
      const mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2
      ctx.fillStyle = 'rgba(239,68,68,0.9)'; ctx.font = '9px Sans-Serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(link.label, mx, my - 6)
    }
    ctx.globalAlpha = 1
  }, [hoverNode, hoveredLinkSet])

  const personNodes = graph.nodes.filter((n) => n.type === 'person')
  const activityNodes = graph.nodes.filter((n) => n.type === 'activity')

  return (
    <div className="flex flex-col gap-3 h-full">
      <div ref={containerRef} className="flex-1 min-h-[520px] rounded-xl overflow-hidden border" style={{ background: '#0f172a' }}>
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graph}
          nodeLabel={(n: any) => n.label}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const { w, h, r } = getNodeDims(node)
            ctx.fillStyle = color
            roundRect(ctx, node.x - w / 2, node.y - h / 2, w, h, r)
            ctx.fill()
          }}
          linkCanvasObject={linkCanvasObject}
          linkCanvasObjectMode={() => 'replace'}
          onNodeHover={(n) => setHoverNode(n ? (n as GraphNode) : null)}
          onNodeClick={(n) => setSelectedNode(selectedNode?.id === (n as GraphNode).id ? null : (n as GraphNode))}
          onEngineStop={() => graphRef.current?.zoomToFit(500, 40)}
          backgroundColor="#0f172a"
          cooldownTicks={120}
        />
      </div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap gap-3">
          <span className="flex items-center gap-1.5"><span className="inline-block h-4 w-10 rounded-full" style={{ background: NODE_COLORS.source }} />Source ({sourceCount})</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-4 w-10 rounded-full" style={{ background: NODE_COLORS.person }} />Person ({personNodes.length})</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-4 w-10 rounded-full" style={{ background: NODE_COLORS.activity }} />Activity ({activityNodes.length})</span>
          <span className="flex items-center gap-1.5 text-red-400">— — connection</span>
        </div>
        <div className="flex items-center gap-2">
          {selectedNode && <span className="font-semibold">{selectedNode.label} <span className="text-muted-foreground font-normal">({selectedNode.type})</span></span>}
          <Button size="sm" variant="outline" className="h-7" onClick={() => graphRef.current?.zoomToFit(400, 40)}>Fit</Button>
        </div>
      </div>
    </div>
  )
}

export default function CommonGraphPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const idsParam = searchParams?.get('ids') ?? ''
  const sourceIds = useMemo(() => idsParam.split(',').filter(Boolean).map((id) => decodeURIComponent(id)), [idsParam])

  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [buildStatus, setBuildStatus] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const [buildResult, setBuildResult] = useState<CommonGraphResponse | null>(null)
  const [isBuilding, setIsBuilding] = useState(false)
  const [graphOpen, setGraphOpen] = useState(false)
  const [selectedModelId, setSelectedModelId] = useState('')
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)

  const { data: models = [] } = useModels()
  const { data: defaults } = useModelDefaults()
  const languageModels = useMemo(() => models.filter((m) => m.type === 'language'), [models])

  useEffect(() => {
    if (!selectedModelId && defaults?.default_transformation_model) setSelectedModelId(defaults.default_transformation_model)
    else if (!selectedModelId && languageModels.length > 0) setSelectedModelId(languageModels[0].id)
  }, [defaults, languageModels, selectedModelId])

  const graphData = useMemo((): GraphData | undefined => {
    const raw = buildResult?.metadata as any
    return raw?.graph ? (raw.graph as GraphData) : undefined
  }, [buildResult])

  const graphHasContent = Boolean(graphData?.nodes?.length && graphData?.links?.length)

  useEffect(() => {
    let isActive = true
    if (sourceIds.length === 0) { setSources([]); setLoading(false); return }
    setLoading(true)
    Promise.all(sourceIds.map((id) => sourcesApi.get(id).catch(() => null)))
      .then((results) => { if (isActive) setSources(results.filter(Boolean) as SourceListResponse[]) })
      .catch(() => { if (isActive) setError('Failed to load selected sources.') })
      .finally(() => { if (isActive) setLoading(false) })
    return () => { isActive = false }
  }, [sourceIds])

  const invalidIds = useMemo(() => sourceIds.filter((id) => !sources.some((s) => s.id === id)), [sourceIds, sources])
  const canBuild = sources.length >= 2 && invalidIds.length === 0

  const handleBuild = async () => {
    if (!canBuild || isBuilding) return
    setBuildError(null); setBuildStatus('Analyzing documents with AI…'); setIsBuilding(true)
    try {
      const result = await sourcesApi.createCommonGraph({ source_ids: sourceIds, model_id: selectedModelId || undefined, prompt: prompt !== DEFAULT_PROMPT ? prompt : undefined })
      setBuildResult(result); setBuildStatus('Network graph built and saved.')
      if (result.id) { const saved = await sourcesApi.getCommonGraph(result.id); setBuildResult(saved) }
    } catch (error) {
      const axiosError = error as AxiosError | undefined
      const detail = (axiosError?.response?.data as any)?.detail || axiosError?.message || (error instanceof Error ? error.message : null)
      setBuildError(detail ?? 'Failed to create graph.'); setBuildStatus(null)
    } finally { setIsBuilding(false) }
  }

  return (
    <AppShell>
      <div className="flex flex-col h-full w-full px-6 py-6">
        <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Create common graph</h1>
            <p className="mt-1 text-muted-foreground max-w-2xl">AI extracts persons, activities, and connections across selected sources and builds a network graph.</p>
          </div>
          <Button variant="outline" onClick={() => router.push('/sources')}>Back to sources</Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.75fr_1fr]">
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader><CardTitle className="text-lg">Selected sources</CardTitle></CardHeader>
              <CardContent>
                {loading ? <p className="text-sm text-muted-foreground">Loading…</p> : error ? <p className="text-sm text-red-500">{error}</p> : (
                  <div className="space-y-3">
                    {sources.map((source) => (
                      <div key={source.id} className="rounded-xl border p-4 bg-background flex items-center justify-between gap-4">
                        <div>
                          <p className="font-semibold">{source.title || 'Untitled source'}</p>
                          <p className="text-sm text-muted-foreground truncate">{source.asset?.url || source.asset?.file_path || 'Source content'}</p>
                        </div>
                        <Badge variant="secondary" className="text-xs">{source.embedded ? 'Embedded' : 'Not embedded'}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-lg">AI extraction prompt</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                    <SelectTrigger><SelectValue placeholder="Select a language model…" /></SelectTrigger>
                    <SelectContent>{languageModels.map((m) => <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Extraction prompt</Label>
                  <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={14} className="font-mono text-xs" />
                  <Button variant="ghost" size="sm" onClick={() => setPrompt(DEFAULT_PROMPT)} className="text-xs">Reset to default</Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle className="text-lg">Graph status</CardTitle></CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">{sources.length > 0 ? `${sources.length} selected source${sources.length === 1 ? '' : 's'}` : 'Select at least two sources.'}</p>
              <Button className="w-full" disabled={!canBuild || isBuilding || !selectedModelId} onClick={handleBuild}>
                {isBuilding ? 'Building…' : 'Build network graph'}
              </Button>
              {buildStatus && <div className="rounded-xl border border-green-200 bg-green-50 p-4 mt-4 text-sm text-green-900">{buildStatus}</div>}
              {buildError && <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 mt-4 text-sm text-destructive">{buildError}</div>}
              {buildResult && graphHasContent && (
                <Button className="mt-4 w-full" onClick={() => setGraphOpen(true)}>View network graph</Button>
              )}
              {buildResult && !graphHasContent && (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">No network data found. Try adjusting the prompt.</div>
              )}
            </CardContent>
          </Card>
        </div>

        <Dialog open={graphOpen} onOpenChange={setGraphOpen}>
          <DialogContent className="w-[min(95vw,1300px)] max-h-[95vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle>Network graph visualization</DialogTitle>
            </DialogHeader>
            <div className="flex-1 min-h-0 overflow-auto p-2">
              {graphHasContent ? (
                <NetworkGraphViewer graph={graphData as GraphData} sourceCount={sources.length} />
              ) : (
                <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Graph data not available.</div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  )
}
