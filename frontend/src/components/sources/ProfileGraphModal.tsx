'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d'
import { sourcesApi } from '@/lib/api/sources'
import { ProfileGraphData } from '@/lib/types/api'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { User, Users, UserCheck, RefreshCw, X } from 'lucide-react'
import { useModels, useModelDefaults } from '@/lib/hooks/use-models'
import { PersonalMindMap, nodeImageStore as personalNodeImageStore } from './PersonalMindMap'

// ── Image store ───────────────────────────────────────────────────────────────
const nodeImageStore = new Map<string, string>()
const loadedImages = new Map<string, HTMLImageElement | null>()

function loadImg(src: string): Promise<HTMLImageElement | null> {
  if (loadedImages.has(src)) return Promise.resolve(loadedImages.get(src)!)
  return new Promise((resolve) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => { loadedImages.set(src, img); resolve(img) }
    img.onerror = () => { loadedImages.set(src, null); resolve(null) }
    img.src = src
  })
}

// ── Draw avatar ───────────────────────────────────────────────────────────────
function drawAvatar(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, r: number,
  label: string, sublabel: string,
  img: HTMLImageElement | null,
  gender: 'male' | 'female',
  isCenter: boolean, isHovered: boolean, dimmed: boolean,
) {
  if (!isFinite(x) || !isFinite(y) || !isFinite(r) || r <= 0) return
  ctx.globalAlpha = dimmed ? 0.18 : 1

  // Glow for center
  if (isCenter) {
    const g = ctx.createRadialGradient(x, y, r, x, y, r + 16)
    g.addColorStop(0, 'rgba(59,130,246,0.45)')
    g.addColorStop(1, 'rgba(59,130,246,0)')
    ctx.beginPath(); ctx.arc(x, y, r + 16, 0, 2 * Math.PI)
    ctx.fillStyle = g; ctx.fill()
  }

  // Outer ring
  ctx.beginPath(); ctx.arc(x, y, r + 3, 0, 2 * Math.PI)
  ctx.fillStyle = isCenter ? '#3b82f6' : (isHovered ? '#60a5fa' : '#cbd5e1')
  ctx.fill()

  // White gap
  ctx.beginPath(); ctx.arc(x, y, r + 1.5, 0, 2 * Math.PI)
  ctx.fillStyle = '#fff'; ctx.fill()

  // Photo or silhouette
  ctx.save()
  ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.clip()
  if (img) {
    ctx.drawImage(img, x - r, y - r, r * 2, r * 2)
  } else {
    ctx.fillStyle = gender === 'female' ? '#fdf2f8' : '#eff6ff'
    ctx.fillRect(x - r, y - r, r * 2, r * 2)
    ctx.fillStyle = gender === 'female' ? '#ec4899' : '#3b82f6'
    ctx.beginPath(); ctx.arc(x, y - r * 0.18, r * 0.36, 0, 2 * Math.PI); ctx.fill()
    ctx.beginPath(); ctx.ellipse(x, y + r * 0.52, r * 0.4, r * 0.36, 0, 0, 2 * Math.PI); ctx.fill()
  }
  ctx.restore()

  // Name
  const nd = label.length > 14 ? label.slice(0, 12) + '…' : label
  ctx.fillStyle = isCenter ? '#1d4ed8' : '#1e293b'
  ctx.font = `${isCenter ? 'bold ' : ''}${isCenter ? 12 : 11}px Sans-Serif`
  ctx.textAlign = 'center'; ctx.textBaseline = 'top'
  ctx.fillText(nd, x, y + r + 5)

  // Sublabel
  if (sublabel && !isCenter) {
    ctx.fillStyle = '#64748b'; ctx.font = '9px Sans-Serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'top'
    ctx.fillText(sublabel, x, y + r + 19)
  }
  ctx.globalAlpha = 1
}

// ── Types ─────────────────────────────────────────────────────────────────────
type PNode = {
  id: string; label: string; sublabel: string
  gender: 'male' | 'female'; isCenter: boolean
  details?: string
  x?: number; y?: number
}
type PLink = { source: string | PNode; target: string | PNode; label?: string }
function gid(n: string | PNode): string { return typeof n === 'string' ? n : n.id }

// ── Avatar Graph ──────────────────────────────────────────────────────────────
function AvatarGraph({ nodes, links }: { nodes: PNode[]; links: PLink[] }) {
  const graphRef = useRef<ForceGraphMethods | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [dims, setDims] = useState({ w: 800, h: 560 })
  const [hoverNode, setHoverNode] = useState<PNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<PNode | null>(null)
  const [selectedPos, setSelectedPos] = useState<{ x: number; y: number } | null>(null)
  const [nodeImgs, setNodeImgs] = useState<Map<string, HTMLImageElement | null>>(new Map())
  const [, forceUpdate] = useState(0)

  // Load stored images on mount
  useEffect(() => {
    const toLoad: { id: string; url: string }[] = []
    nodes.forEach((n) => { const u = nodeImageStore.get(n.id); if (u) toLoad.push({ id: n.id, url: u }) })
    if (!toLoad.length) return
    Promise.all(toLoad.map(async ({ id, url }) => ({ id, img: await loadImg(url) })))
      .then((res) => setNodeImgs((prev) => { const m = new Map(prev); res.forEach(({ id, img }) => m.set(id, img)); return m }))
  }, [nodes])

  useEffect(() => {
    const el = containerRef.current; if (!el) return
    const obs = new ResizeObserver((e) => {
      const r = e[0].contentRect
      setDims({ w: Math.max(400, Math.round(r.width)), h: Math.max(400, Math.round(r.height)) })
    })
    obs.observe(el); return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const fg = graphRef.current; if (!fg) return
    fg.d3Force('charge')?.strength(-450)
    fg.d3Force('link')?.distance(160)
  }, [dims])

  const connectedIds = useMemo(() => {
    if (!hoverNode) return new Set<string>()
    const ids = new Set<string>()
    links.forEach((l) => { const s = gid(l.source), t = gid(l.target); if (s === hoverNode.id) ids.add(t); if (t === hoverNode.id) ids.add(s) })
    return ids
  }, [links, hoverNode])

  // Upload image for a node
  const handleUpload = useCallback((nodeId: string, file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const url = e.target?.result as string
      nodeImageStore.set(nodeId, url)
      loadedImages.delete(url)
      loadImg(url).then((img) => {
        setNodeImgs((prev) => new Map(prev).set(nodeId, img))
        forceUpdate((n) => n + 1)
      })
    }
    reader.readAsDataURL(file)
  }, [])

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const isHovered = hoverNode?.id === node.id
    const isSelected = selectedNode?.id === node.id
    const isConnected = connectedIds.has(node.id)
    const dimmed = !!(hoverNode && !isHovered && !isConnected)
    const r = node.isCenter ? 38 : 26
    const img = nodeImgs.get(node.id) ?? null
    drawAvatar(ctx, node.x, node.y, r, node.label, node.sublabel, img, node.gender, node.isCenter, isHovered || isSelected, dimmed)
  }, [hoverNode, selectedNode, connectedIds, nodeImgs])

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const s = link.source, t = link.target
    if (!s?.x || !t?.x) return
    const isHl = hoverNode && (gid(s) === hoverNode.id || gid(t) === hoverNode.id)
    const dimmed = hoverNode && !isHl
    ctx.globalAlpha = dimmed ? 0.05 : (isHl ? 0.85 : 0.3)
    ctx.strokeStyle = isHl ? '#3b82f6' : '#94a3b8'
    ctx.lineWidth = isHl ? 2 : 1.2
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke()
    if (link.label) {
      const mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2
      ctx.globalAlpha = dimmed ? 0.08 : (isHl ? 1 : 0.65)
      const tw = ctx.measureText(link.label).width + 10
      ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.fillRect(mx - tw / 2, my - 8, tw, 15)
      ctx.fillStyle = isHl ? '#1d4ed8' : '#475569'
      ctx.font = `${isHl ? 'bold ' : ''}9px Sans-Serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(link.label, mx, my)
    }
    ctx.globalAlpha = 1
  }, [hoverNode])

  // Convert canvas coords to container-relative screen coords
  const canvasToScreen = useCallback((cx: number, cy: number) => {
    const fg = graphRef.current as any
    if (!fg) return null
    try {
      const zoom = fg.zoom?.() ?? 1
      const pan = fg.centerAt?.() ?? { x: 0, y: 0 }
      const el = containerRef.current
      if (!el) return null
      const rect = el.getBoundingClientRect()
      const sx = (cx - pan.x) * zoom + rect.width / 2
      const sy = (cy - pan.y) * zoom + rect.height / 2
      return { x: sx, y: sy }
    } catch { return null }
  }, [])

  const handleNodeClick = useCallback((node: any) => {
    const n = node as PNode
    if (selectedNode?.id === n.id) {
      setSelectedNode(null); setSelectedPos(null); return
    }
    setSelectedNode(n)
    // Try to get screen position
    const pos = canvasToScreen(n.x ?? 0, n.y ?? 0)
    setSelectedPos(pos)
  }, [selectedNode, canvasToScreen])

  return (
    <div className="relative flex flex-col h-full gap-0">
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file && selectedNode) handleUpload(selectedNode.id, file)
          e.target.value = ''
        }}
      />

      <div ref={containerRef} className="flex-1 min-h-0 rounded-xl overflow-hidden" style={{ background: '#f1f5f9' }}>
        <ForceGraph2D
          ref={graphRef}
          width={dims.w}
          height={dims.h}
          graphData={{ nodes, links }}
          nodeLabel={() => ''}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            if (!isFinite(node.x) || !isFinite(node.y)) return
            ctx.fillStyle = color
            ctx.beginPath(); ctx.arc(node.x, node.y, node.isCenter ? 44 : 32, 0, 2 * Math.PI); ctx.fill()
          }}
          linkCanvasObject={linkCanvasObject}
          linkCanvasObjectMode={() => 'replace'}
          onNodeHover={(n) => setHoverNode(n ? (n as PNode) : null)}
          onNodeClick={handleNodeClick}
          onEngineStop={() => graphRef.current?.zoomToFit(500, 80)}
          backgroundColor="#f1f5f9"
          cooldownTicks={120}
        />
      </div>

      {/* Detail popup — positioned near node or bottom-center */}
      {selectedNode && (
        <div
          className="absolute z-20 w-72 rounded-2xl bg-white shadow-2xl border border-slate-100 overflow-hidden"
          style={
            selectedPos
              ? {
                  left: Math.min(Math.max(selectedPos.x - 144, 8), dims.w - 296),
                  top: Math.min(selectedPos.y + 50, dims.h - 200),
                }
              : { bottom: 12, left: '50%', transform: 'translateX(-50%)' }
          }
        >
          {/* Header with photo */}
          <div className={`flex items-center gap-3 p-4 ${selectedNode.gender === 'female' ? 'bg-pink-50' : 'bg-blue-50'}`}>
            {/* Clickable avatar — click to upload */}
            <button
              className="relative flex-shrink-0 group"
              title="Click to upload photo"
              onClick={() => fileRef.current?.click()}
            >
              <div className="h-14 w-14 rounded-full overflow-hidden border-2 border-white shadow-md">
                {nodeImageStore.get(selectedNode.id) ? (
                  <img src={nodeImageStore.get(selectedNode.id)} alt={selectedNode.label} className="h-full w-full object-cover" />
                ) : (
                  <div className={`h-full w-full flex items-center justify-center ${selectedNode.gender === 'female' ? 'bg-pink-100' : 'bg-blue-100'}`}>
                    <User className={`h-7 w-7 ${selectedNode.gender === 'female' ? 'text-pink-400' : 'text-blue-400'}`} />
                  </div>
                )}
              </div>
              {/* Upload overlay on hover */}
              <div className="absolute inset-0 rounded-full bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                <span className="text-white text-xs font-medium">📷</span>
              </div>
            </button>

            <div className="flex-1 min-w-0">
              <p className="font-bold text-slate-900 text-sm leading-tight">{selectedNode.label}</p>
              {selectedNode.sublabel && (
                <Badge variant="outline" className="mt-1 text-xs capitalize border-slate-300">{selectedNode.sublabel}</Badge>
              )}
            </div>

            <button onClick={() => { setSelectedNode(null); setSelectedPos(null) }} className="text-slate-400 hover:text-slate-600 flex-shrink-0">
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Details */}
          {selectedNode.details && (
            <div className="px-4 py-3 text-sm text-slate-600 border-t border-slate-100 leading-relaxed">
              {selectedNode.details}
            </div>
          )}

          {!selectedNode.details && (
            <div className="px-4 py-2 text-xs text-slate-400 border-t border-slate-100">
              No additional details available.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ProfileGraphModal({ open, onOpenChange, sourceId, sourceTitle, sourceImageUrl }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceId: string
  sourceTitle?: string
  sourceImageUrl?: string
}) {
  const [data, setData] = useState<ProfileGraphData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('personal')

  const { data: models = [] } = useModels()
  const { data: defaults } = useModelDefaults()
  const modelId = useMemo(() => {
    return defaults?.default_transformation_model || models.find((m) => m.type === 'language')?.id || ''
  }, [defaults, models])

  useEffect(() => {
    if (!open || !sourceId) return
    setLoading(true); setError(null)
    sourcesApi.getProfileGraph(sourceId, modelId || undefined)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e?.response?.data?.detail || e?.message || 'Failed'); setLoading(false) })
  }, [open, sourceId, modelId])

  useEffect(() => {
    if (!open) { setData(null); setActiveTab('personal') }
  }, [open])

  const centerGender = useMemo((): 'male' | 'female' =>
    (data?.personal?.gender || data?.personal?.Gender || '').toLowerCase().includes('female') ? 'female' : 'male',
    [data]
  )

  const centerNode = useMemo((): PNode => ({
    id: `center_${sourceId}`,
    label: data?.main_person || sourceTitle || 'Main',
    sublabel: data?.personal?.role || data?.personal?.Role || '',
    gender: centerGender,
    isCenter: true,
    details: '',
  }), [data, sourceId, sourceTitle, centerGender])

  const familyGraph = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const nodes: PNode[] = [centerNode]
    const links: PLink[] = []
    data.family.forEach((p, i) => {
      const nid = `fam_${sourceId}_${i}`
      nodes.push({ id: nid, label: p.name, sublabel: p.relation, gender: p.gender as 'male' | 'female', isCenter: false, details: p.details })
      links.push({ source: centerNode.id, target: nid, label: p.relation })
    })
    return { nodes, links }
  }, [data, centerNode, sourceId])

  const associatesGraph = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const nodes: PNode[] = [centerNode]
    const links: PLink[] = []
    data.associates.forEach((p, i) => {
      const nid = `assoc_${sourceId}_${i}`
      nodes.push({ id: nid, label: p.name, sublabel: p.relation, gender: p.gender as 'male' | 'female', isCenter: false, details: p.details })
      links.push({ source: centerNode.id, target: nid, label: p.relation })
    })
    return { nodes, links }
  }, [data, centerNode, sourceId])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex flex-col overflow-hidden p-0"
        style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          width: '100vw', height: '100vh',
          maxWidth: '100vw', maxHeight: '100vh',
          margin: 0, borderRadius: 0, transform: 'none', translate: 'none',
        }}
      >
        <DialogHeader className="flex-shrink-0 px-6 pt-4 pb-3 border-b bg-white">
          <DialogTitle className="flex items-center gap-2 flex-wrap">
            <User className="h-5 w-5 text-blue-500" />
            <span>Profile — {sourceTitle || 'Source'}</span>
            {data && (
              <>
                <Badge variant="outline" className="text-blue-600 border-blue-300 font-normal">{data.main_person || 'Unknown'}</Badge>
                {data.family.length > 0 && <Badge variant="outline" className="text-green-600 border-green-300">{data.family.length} family</Badge>}
                {data.associates.length > 0 && <Badge variant="outline" className="text-amber-600 border-amber-300">{data.associates.length} associates</Badge>}
              </>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-hidden bg-slate-50">
          {loading ? (
            <div className="flex h-full items-center justify-center gap-3">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
              <span className="text-slate-500">Extracting profile with AI…</span>
            </div>
          ) : error ? (
            <div className="flex h-full items-center justify-center p-8">
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 max-w-md text-center">{error}</div>
            </div>
          ) : data ? (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <TabsList className="mx-6 mt-3 flex-shrink-0 bg-white border">
                <TabsTrigger value="personal" className="flex items-center gap-1.5">
                  <UserCheck className="h-4 w-4" /> Personal Details
                </TabsTrigger>
                <TabsTrigger value="family" className="flex items-center gap-1.5" disabled={data.family.length === 0}>
                  <Users className="h-4 w-4" /> Family ({data.family.length})
                </TabsTrigger>
                <TabsTrigger value="associates" className="flex items-center gap-1.5" disabled={data.associates.length === 0}>
                  <User className="h-4 w-4" /> Friends & Associates ({data.associates.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="personal" className="flex-1 min-h-0 overflow-hidden">
                <PersonalMindMap data={data.personal} mainPerson={data.main_person} sourceId={sourceId} sourceImageUrl={sourceImageUrl} />
              </TabsContent>

              <TabsContent value="family" className="flex-1 min-h-0 p-4 overflow-hidden">
                {data.family.length > 0
                  ? <AvatarGraph nodes={familyGraph.nodes} links={familyGraph.links} />
                  : <div className="flex h-40 items-center justify-center text-slate-400 text-sm">No family members found.</div>}
              </TabsContent>

              <TabsContent value="associates" className="flex-1 min-h-0 p-4 overflow-hidden">
                {data.associates.length > 0
                  ? <AvatarGraph nodes={associatesGraph.nodes} links={associatesGraph.links} />
                  : <div className="flex h-40 items-center justify-center text-slate-400 text-sm">No friends or associates found.</div>}
              </TabsContent>
            </Tabs>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
