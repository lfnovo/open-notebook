'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d'
import { sourcesApi } from '@/lib/api/sources'
import { CommonGraphResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
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
import { useModels, useModelDefaults, useUpdateModelDefaults } from '@/lib/hooks/use-models'
import { Badge } from '@/components/ui/badge'
import { useTransformations, useCreateTransformation, useUpdateTransformation } from '@/lib/hooks/use-transformations'
import { Settings2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

const COMMON_GRAPH_TRANSFORMATION_NAME = 'common_graph_extraction'

// No hardcoded default — prompt always comes from saved transformation
const FALLBACK_PROMPT_HINT = `(Prompt loaded from Transformations)

Note: Person name extraction uses NLP (spaCy) for accuracy.
The prompt here is saved as a transformation for reference/customization.`

const SOURCE_LINK_COLORS = [
  { line: 'rgba(168,85,247,0.6)', glow: '#a855f7' },
  { line: 'rgba(251,146,60,0.6)', glow: '#fb923c' },
  { line: 'rgba(34,211,238,0.6)', glow: '#22d3ee' },
  { line: 'rgba(74,222,128,0.6)', glow: '#4ade80' },
  { line: 'rgba(251,191,36,0.6)', glow: '#fbbf24' },
]

const NODE_TYPE_COLORS: Record<string, string> = {
  source: '#a855f7',
  person: '#0ea5e9',
  relative: '#22c55e',
  activity: '#f59e0b',
  entity: '#94a3b8',
  term: '#94a3b8',
}

const ACTIVITY_TYPE_COLORS: Record<string, string> = {
  crime: '#ef4444',
  weapon: '#dc2626',
  drug: '#f97316',
  transaction: '#eab308',
  event: '#8b5cf6',
}

type GraphNode = {
  id: string
  label: string
  type: 'source' | 'person' | 'relative' | 'activity' | 'entity' | 'term'
  common?: boolean
  weight?: number
  role?: string
  activity_type?: string
  x?: number
  y?: number
}

type GraphLink = {
  source: string | GraphNode
  target: string | GraphNode
  type?: string
  weight?: number
}

type GraphData = { nodes: GraphNode[]; links: GraphLink[] }

function getNodeId(n: string | GraphNode): string {
  return typeof n === 'string' ? n : n.id
}

function NetworkGraphViewer({ graph }: { graph: GraphData }) {
  const graphRef = useRef<ForceGraphMethods | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
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

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((e) => {
      const r = e[0].contentRect
      setDimensions({ width: Math.max(400, Math.round(r.width)), height: Math.max(400, Math.round(r.height)) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const fg = graphRef.current
    if (!fg) return
    fg.d3Force('charge')?.strength(-500)
    fg.d3Force('link')?.distance(180)
  }, [dimensions])

  const getSourceIdx = useCallback((nodeId: string) => {
    const m = nodeId.match(/^source:(\d+)$/)
    return m ? parseInt(m[1]) : 0
  }, [])

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const isHovered = hoverNode?.id === node.id
    const isConnected = connectedNodeIds.has(node.id)
    const dimmed = hoverNode && !isHovered && !isConnected
    const isSource = node.type === 'source'
    const isPerson = node.type === 'person'
    const isRelative = node.type === 'relative'
    const isActivity = node.type === 'activity'
    const radius = isSource ? 36 : isPerson ? (node.common ? 22 : 18) : isRelative ? 14 : isActivity ? (node.common ? 18 : 14) : 16

    ctx.globalAlpha = dimmed ? 0.08 : 1
    const nodeColor = isActivity
      ? (ACTIVITY_TYPE_COLORS[node.activity_type || ''] || '#f59e0b')
      : (NODE_TYPE_COLORS[node.type] || '#94a3b8')
    if (isHovered) { ctx.shadowColor = nodeColor; ctx.shadowBlur = 28 }

    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    if (isSource) ctx.fillStyle = SOURCE_LINK_COLORS[getSourceIdx(node.id) % SOURCE_LINK_COLORS.length].glow
    else if (isPerson) ctx.fillStyle = node.common ? '#0ea5e9' : 'rgba(14,165,233,0.7)'
    else if (isRelative) ctx.fillStyle = 'rgba(34,197,94,0.85)'
    else if (isActivity) ctx.fillStyle = ACTIVITY_TYPE_COLORS[node.activity_type || ''] || '#f59e0b'
    else ctx.fillStyle = node.common ? 'rgba(148,163,184,0.95)' : 'rgba(100,116,139,0.7)'
    ctx.fill()
    ctx.strokeStyle = isHovered ? '#fff' : 'rgba(255,255,255,0.25)'
    ctx.lineWidth = isHovered ? 2.5 : (node.common ? 1.5 : 0.8)
    ctx.stroke()
    ctx.shadowBlur = 0

    const label = node.label || ''
    if (isSource) {
      const words = label.replace(/\.docx?$/i, '').split(/[\s_-]+/)
      ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Sans-Serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      const half = Math.ceil(words.length / 2)
      const l1 = words.slice(0, half).join(' ').slice(0, 14)
      const l2 = words.slice(half).join(' ').slice(0, 14)
      if (l2) { ctx.fillText(l1, node.x, node.y - 7); ctx.fillText(l2, node.x, node.y + 7) }
      else ctx.fillText(l1, node.x, node.y)
    } else {
      const disp = label.length > 18 ? label.slice(0, 16) + '…' : label
      ctx.fillStyle = 'rgba(226,232,240,0.95)'
      ctx.font = `${isPerson ? 'bold ' : ''}10px Sans-Serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      ctx.fillText(disp, node.x, node.y + radius + 3)    }
    ctx.globalAlpha = 1
  }, [hoverNode, connectedNodeIds, getSourceIdx])

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const s = link.source, t = link.target
    if (!s?.x || !t?.x) return
    const isRelationLink = link.type === 'relation'
    const srcNodeId = getNodeId(s).startsWith('source:') ? getNodeId(s) : getNodeId(t)
    const isHighlighted = hoverNode && (getNodeId(s) === hoverNode.id || getNodeId(t) === hoverNode.id)
    const dimmed = hoverNode && !isHighlighted

    ctx.globalAlpha = dimmed ? 0.03 : (isHighlighted ? 0.95 : 0.5)

    if (isRelationLink) {
      ctx.strokeStyle = isHighlighted ? '#22c55e' : 'rgba(34,197,94,0.6)'
      ctx.lineWidth = isHighlighted ? 2 : 1.2
      ctx.setLineDash([5, 3])
    } else {
      const col = SOURCE_LINK_COLORS[getSourceIdx(srcNodeId) % SOURCE_LINK_COLORS.length]
      ctx.strokeStyle = isHighlighted ? col.glow : col.line
      ctx.lineWidth = isHighlighted ? 2 : 1
      ctx.setLineDash([])
    }
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke()
    ctx.setLineDash([])

    // Show relation label on hover
    if (isHighlighted && isRelationLink && link.label) {
      const mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2
      ctx.globalAlpha = 1
      const tw = ctx.measureText(link.label).width + 8
      ctx.fillStyle = 'rgba(0,0,0,0.75)'
      ctx.fillRect(mx - tw / 2, my - 9, tw, 16)
      ctx.fillStyle = '#22c55e'
      ctx.font = 'bold 9px Sans-Serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(link.label, mx, my)
    }
    ctx.globalAlpha = 1
  }, [hoverNode, getSourceIdx])

  const entityNodes = graph.nodes.filter((n) => n.type === 'person' || n.type === 'entity' || n.type === 'term')
  const relativeNodes = graph.nodes.filter((n) => n.type === 'relative')
  const activityNodes = graph.nodes.filter((n) => n.type === 'activity')
  const sourceNodes = graph.nodes.filter((n) => n.type === 'source')

  return (
    <div className="flex flex-col h-full gap-2">
      <div ref={containerRef} className="flex-1 min-h-0 rounded-lg overflow-hidden" style={{ background: '#0a0f1e' }}>
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graph}
          nodeLabel={(n: any) => n.label}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(node.x, node.y, node.type === 'source' ? 40 : 26, 0, 2 * Math.PI)
            ctx.fill()
          }}
          linkCanvasObject={linkCanvasObject}
          linkCanvasObjectMode={() => 'replace'}
          onNodeHover={(n) => setHoverNode(n ? (n as GraphNode) : null)}
          onNodeClick={(n) => setSelectedNode(selectedNode?.id === (n as GraphNode).id ? null : (n as GraphNode))}
          onEngineStop={() => graphRef.current?.zoomToFit(500, 60)}
          backgroundColor="#0a0f1e"
          cooldownTicks={150}
        />
      </div>
      <div className="flex items-center justify-between gap-3 px-1 text-xs flex-shrink-0">
        <div className="flex flex-wrap gap-3">
          {sourceNodes.map((n, i) => (
            <span key={n.id} className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-full" style={{ background: SOURCE_LINK_COLORS[i % SOURCE_LINK_COLORS.length].glow }} />
              {n.label.length > 24 ? n.label.slice(0, 22) + '…' : n.label}
            </span>
          ))}
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full bg-sky-400" />
            Persons ({entityNodes.filter((n: any) => n.common).length} common / {entityNodes.filter((n: any) => !n.common).length} unique)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full bg-green-500" />
            Relatives ({relativeNodes.length})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full bg-amber-400" />
            Activities ({activityNodes.filter((n: any) => n.common).length} common / {activityNodes.filter((n: any) => !n.common).length} unique)
          </span>
          <span className="flex items-center gap-1.5 text-green-400">- - relation</span>
        </div>
        <div className="flex items-center gap-2">
          {selectedNode && <span className="rounded border border-slate-600 bg-slate-800 text-white px-2 py-0.5 font-medium">{selectedNode.label}</span>}
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => graphRef.current?.zoomToFit(400, 60)}>Fit</Button>
        </div>
      </div>
    </div>
  )
}

interface CommonGraphModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceIds: string[]
}

export function CommonGraphModal({ open, onOpenChange, sourceIds }: CommonGraphModalProps) {
  const [selectedModelId, setSelectedModelId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [isBuilding, setIsBuilding] = useState(false)
  const [buildResult, setBuildResult] = useState<CommonGraphResponse | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [savedTransformationId, setSavedTransformationId] = useState<string | null>(null)

  const { data: models = [] } = useModels()
  const { data: defaults } = useModelDefaults()
  const updateDefaults = useUpdateModelDefaults()
  const { data: transformations = [] } = useTransformations()
  const createTransformation = useCreateTransformation()
  const updateTransformation = useUpdateTransformation()

  const languageModels = useMemo(() => models.filter((m) => m.type === 'language'), [models])

  // Load saved model from defaults
  useEffect(() => {
    if (!selectedModelId && defaults?.default_transformation_model) {
      setSelectedModelId(defaults.default_transformation_model)
    } else if (!selectedModelId && languageModels.length > 0) {
      setSelectedModelId(languageModels[0].id)
    }
  }, [defaults, languageModels, selectedModelId])

  // Load saved prompt from transformations
  useEffect(() => {
    const existing = transformations.find((t) => t.name === COMMON_GRAPH_TRANSFORMATION_NAME)
    if (existing) {
      setPrompt(existing.prompt)
      setSavedTransformationId(existing.id)
    }
    // If no saved transformation, prompt stays empty — NLP handles extraction
  }, [transformations])

  // Auto-build when modal opens with sources
  useEffect(() => {
    if (open && sourceIds.length >= 2 && selectedModelId && !isBuilding && !buildResult) {
      handleBuild()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, selectedModelId])

  // Reset when closed
  useEffect(() => {
    if (!open) {
      setBuildResult(null)
      setBuildError(null)
      setShowSettings(false)
    }
  }, [open])

  const graphData = useMemo((): GraphData | undefined => {
    const raw = buildResult?.metadata as any
    return raw?.graph ? (raw.graph as GraphData) : undefined
  }, [buildResult])

  const graphHasContent = Boolean(graphData?.nodes?.length && graphData?.links?.length)
  const entityCount = useMemo(() => graphData?.nodes?.filter((n) => n.type === 'person' || n.type === 'entity' || n.type === 'term').length ?? 0, [graphData])
  const commonCount = useMemo(() => graphData?.nodes?.filter((n: any) => n.common).length ?? 0, [graphData])
  const relativeCount = useMemo(() => graphData?.nodes?.filter((n: any) => n.type === 'relative').length ?? 0, [graphData])
  const activityCount = useMemo(() => graphData?.nodes?.filter((n: any) => n.type === 'activity').length ?? 0, [graphData])

  const handleBuild = async () => {
    if (isBuilding || sourceIds.length < 2 || !selectedModelId) return
    setBuildError(null)
    setIsBuilding(true)
    setShowSettings(false)
    try {
      const result = await sourcesApi.createCommonGraph({
        source_ids: sourceIds,
        model_id: selectedModelId,
        // prompt not sent — backend uses NLP for extraction
      })
      const saved = result.id ? await sourcesApi.getCommonGraph(result.id) : result
      setBuildResult(saved)
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to build graph.'
      setBuildError(detail)
    } finally {
      setIsBuilding(false)
    }
  }

  const handleSaveSettings = async () => {
    // Save model as default transformation model
    if (selectedModelId && selectedModelId !== defaults?.default_transformation_model) {
      await updateDefaults.mutateAsync({ default_transformation_model: selectedModelId })
    }

    // Save prompt to transformations (for reference/future use)
    if (prompt.trim()) {
      try {
        if (savedTransformationId) {
          await updateTransformation.mutateAsync({
            id: savedTransformationId,
            data: { prompt, name: COMMON_GRAPH_TRANSFORMATION_NAME, title: 'Common Graph Extraction' }
          })
        } else {
          const created = await createTransformation.mutateAsync({
            name: COMMON_GRAPH_TRANSFORMATION_NAME,
            title: 'Common Graph Extraction',
            description: 'Reference prompt for common graph entity extraction (NLP handles actual extraction)',
            prompt,
            apply_default: false,
          })
          setSavedTransformationId(created.id)
        }
        toast.success('Settings saved')
      } catch {
        toast.error('Failed to save settings')
      }
    }

    handleBuild()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex flex-col overflow-hidden p-0"
        style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          width: '100vw', height: '100vh',
          maxWidth: '100vw', maxHeight: '100vh',
          margin: 0, borderRadius: 0,
          transform: 'none', translate: 'none',
        }}
      >
        {/* Header */}
        <DialogHeader className="flex-shrink-0 px-6 pt-4 pb-3 border-b flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <DialogTitle>Common graph</DialogTitle>
            <Badge variant="secondary">{sourceIds.length} sources</Badge>
            {graphHasContent && (
              <>
                <Badge variant="outline" className="text-sky-500 border-sky-400">{entityCount} persons</Badge>
                <Badge variant="outline" className="text-amber-500 border-amber-400">{activityCount} activities</Badge>
                <Badge variant="outline" className="text-green-600 border-green-400">{commonCount} common</Badge>
                {relativeCount > 0 && <Badge variant="outline" className="text-emerald-500 border-emerald-400">{relativeCount} relatives</Badge>}
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5"
              onClick={() => setShowSettings((v) => !v)}
            >
              <Settings2 className="h-3.5 w-3.5" />
              {showSettings ? 'Hide settings' : 'Settings'}
            </Button>
            <Button
              size="sm"
              className="h-8 gap-1.5"
              disabled={isBuilding || !selectedModelId}
              onClick={handleBuild}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isBuilding ? 'animate-spin' : ''}`} />
              {isBuilding ? 'Building…' : 'Rebuild'}
            </Button>
          </div>
        </DialogHeader>

        {/* Main content */}
        <div className="flex-1 min-h-0 flex overflow-hidden">
          {/* Graph area */}
          <div className="flex-1 min-w-0 p-3 flex flex-col">
            {isBuilding ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ background: '#0a0f1e', borderRadius: 8 }}>
                <RefreshCw className="h-8 w-8 animate-spin text-purple-400" />
                <p className="text-slate-400 text-sm">Analyzing documents and extracting entities…</p>
              </div>
            ) : buildError ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive max-w-md text-center">
                  {buildError}
                  <Button size="sm" variant="outline" className="mt-3 w-full" onClick={handleBuild}>Retry</Button>
                </div>
              </div>
            ) : graphHasContent ? (
              <NetworkGraphViewer graph={graphData as GraphData} />
            ) : (
              <div className="flex-1 flex items-center justify-center" style={{ background: '#0a0f1e', borderRadius: 8 }}>
                <p className="text-slate-500 text-sm">Select at least 2 sources and click Rebuild.</p>
              </div>
            )}
          </div>

          {/* Settings panel — slides in from right */}
          {showSettings && (
            <div className="w-96 flex-shrink-0 border-l flex flex-col overflow-hidden">
              <div className="flex-1 overflow-y-auto p-4 space-y-5">

                {/* Model selector */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Model</Label>
                  <p className="text-xs text-muted-foreground">Language model used for entity extraction.</p>
                  <Select value={selectedModelId} onValueChange={setSelectedModelId}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a language model…" />
                    </SelectTrigger>
                    <SelectContent>
                      {languageModels.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          <div className="flex items-center justify-between w-full gap-3">
                            <span>{m.name}</span>
                            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{m.provider}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Transformation picker */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Extraction Prompt</Label>
                  <p className="text-xs text-muted-foreground">Pick a transformation or use the default common graph prompt.</p>
                  <Select
                    value={savedTransformationId || '__none__'}
                    onValueChange={(val) => {
                      if (val === '__none__') {
                        setPrompt('')
                        setSavedTransformationId(null)
                      } else {
                        const t = transformations.find((t) => t.id === val)
                        if (t) { setPrompt(t.prompt); setSavedTransformationId(t.id) }
                      }
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a transformation…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">
                        <span className="text-muted-foreground">None (NLP only)</span>
                      </SelectItem>
                      {transformations.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          <div className="flex flex-col">
                            <span>{t.title || t.name}</span>
                            {t.description && <span className="text-xs text-muted-foreground">{t.description}</span>}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Prompt preview / edit */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Prompt (saved to Transformations)</Label>
                  <p className="text-xs text-muted-foreground">
                    This prompt is saved as a transformation for reference. Person name extraction uses NLP (spaCy) for accuracy — not the LLM.
                  </p>
                  <Textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={14}
                    className="font-mono text-xs"
                    placeholder="Optional: add notes or instructions here. Actual extraction uses NLP."
                  />
                </div>
              </div>

              <div className="flex-shrink-0 p-4 border-t">
                <Button className="w-full" onClick={handleSaveSettings} disabled={isBuilding}>
                  Save & Rebuild
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
