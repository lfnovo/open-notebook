'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d'
import { sourcesApi } from '@/lib/api/sources'
import { ProfileGraphData } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { User, Users, UserCheck, RefreshCw } from 'lucide-react'

// ── Avatar image cache ────────────────────────────────────────────────────────
const imageCache = new Map<string, HTMLImageElement | null>()

function loadImage(src: string): Promise<HTMLImageElement | null> {
  if (imageCache.has(src)) return Promise.resolve(imageCache.get(src)!)
  return new Promise((resolve) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => { imageCache.set(src, img); resolve(img) }
    img.onerror = () => { imageCache.set(src, null); resolve(null) }
    img.src = src
  })
}

// ── Draw avatar node ──────────────────────────────────────────────────────────
function drawAvatarNode(
  ctx: CanvasRenderingContext2D,
  x: number, y: number,
  radius: number,
  label: string,
  sublabel: string,
  image: HTMLImageElement | null,
  gender: 'male' | 'female' | 'center',
  isHovered: boolean,
  dimmed: boolean,
  isCenter: boolean,
) {
  ctx.globalAlpha = dimmed ? 0.15 : 1

  // Shadow / glow
  if (isHovered || isCenter) {
    ctx.shadowColor = isCenter ? '#3b82f6' : '#60a5fa'
    ctx.shadowBlur = isCenter ? 24 : 16
  }

  // Outer ring
  ctx.beginPath()
  ctx.arc(x, y, radius + 3, 0, 2 * Math.PI)
  ctx.fillStyle = isCenter ? '#3b82f6' : (isHovered ? '#60a5fa' : '#e2e8f0')
  ctx.fill()

  // White inner ring
  ctx.beginPath()
  ctx.arc(x, y, radius + 1, 0, 2 * Math.PI)
  ctx.fillStyle = '#ffffff'
  ctx.fill()

  // Clip circle for avatar
  ctx.save()
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, 2 * Math.PI)
  ctx.clip()

  if (image) {
    // Draw photo
    ctx.drawImage(image, x - radius, y - radius, radius * 2, radius * 2)
  } else {
    // Draw gender icon background
    ctx.fillStyle = isCenter ? '#dbeafe' : (gender === 'female' ? '#fce7f3' : '#dbeafe')
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2)

    // Draw silhouette
    const color = isCenter ? '#3b82f6' : (gender === 'female' ? '#ec4899' : '#3b82f6')
    ctx.fillStyle = color

    // Head
    ctx.beginPath()
    ctx.arc(x, y - radius * 0.2, radius * 0.38, 0, 2 * Math.PI)
    ctx.fill()

    // Body
    ctx.beginPath()
    ctx.ellipse(x, y + radius * 0.55, radius * 0.42, radius * 0.38, 0, 0, 2 * Math.PI)
    ctx.fill()
  }

  ctx.restore()
  ctx.shadowBlur = 0

  // Label below node
  if (label) {
    const disp = label.length > 14 ? label.slice(0, 12) + '…' : label
    ctx.fillStyle = isCenter ? '#1e40af' : '#1e293b'
    ctx.font = `${isCenter ? 'bold ' : ''}11px Sans-Serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(disp, x, y + radius + 5)
  }

  // Sublabel (relation)
  if (sublabel && !isCenter) {
    ctx.fillStyle = '#64748b'
    ctx.font = '9px Sans-Serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(sublabel, x, y + radius + 18)
  }

  ctx.globalAlpha = 1
}

// ── Graph types ───────────────────────────────────────────────────────────────
type PNode = {
  id: string
  label: string
  sublabel: string
  gender: 'male' | 'female' | 'center'
  isCenter: boolean
  imageUrl?: string
  x?: number
  y?: number
}

type PLink = { source: string | PNode; target: string | PNode; label?: string }

function getNodeId(n: string | PNode): string {
  return typeof n === 'string' ? n : n.id
}

// ── Avatar Network Graph ──────────────────────────────────────────────────────
function AvatarGraph({
  nodes,
  links,
  centerImageUrl,
}: {
  nodes: PNode[]
  links: PLink[]
  centerImageUrl?: string
}) {
  const graphRef = useRef<ForceGraphMethods | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 560 })
  const [hoverNode, setHoverNode] = useState<PNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<PNode | null>(null)
  const [images, setImages] = useState<Map<string, HTMLImageElement | null>>(new Map())

  // Load images
  useEffect(() => {
    const toLoad: Array<{ id: string; url: string }> = []
    nodes.forEach((n) => {
      if (n.imageUrl) toLoad.push({ id: n.id, url: n.imageUrl })
    })
    if (centerImageUrl) toLoad.push({ id: '__center__', url: centerImageUrl })

    Promise.all(
      toLoad.map(async ({ id, url }) => {
        const img = await loadImage(url)
        return { id, img }
      })
    ).then((results) => {
      const map = new Map<string, HTMLImageElement | null>()
      results.forEach(({ id, img }) => map.set(id, img))
      setImages(map)
    })
  }, [nodes, centerImageUrl])

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
    fg.d3Force('charge')?.strength(-400)
    fg.d3Force('link')?.distance(130)
  }, [dimensions])

  const connectedIds = useMemo(() => {
    if (!hoverNode) return new Set<string>()
    const ids = new Set<string>()
    links.forEach((l) => {
      const s = getNodeId(l.source), t = getNodeId(l.target)
      if (s === hoverNode.id) ids.add(t)
      if (t === hoverNode.id) ids.add(s)
    })
    return ids
  }, [links, hoverNode])

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const isHovered = hoverNode?.id === node.id
    const isConnected = connectedIds.has(node.id)
    const dimmed = !!(hoverNode && !isHovered && !isConnected)
    const radius = node.isCenter ? 36 : 24
    const img = node.isCenter ? (images.get('__center__') ?? null) : (node.imageUrl ? images.get(node.id) ?? null : null)

    drawAvatarNode(
      ctx, node.x, node.y, radius,
      node.label, node.sublabel,
      img, node.gender,
      isHovered, dimmed, node.isCenter
    )
  }, [hoverNode, connectedIds, images])

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const s = link.source, t = link.target
    if (!s?.x || !t?.x) return
    const isHighlighted = hoverNode && (getNodeId(s) === hoverNode.id || getNodeId(t) === hoverNode.id)
    const dimmed = hoverNode && !isHighlighted

    ctx.globalAlpha = dimmed ? 0.05 : (isHighlighted ? 0.9 : 0.35)
    ctx.strokeStyle = isHighlighted ? '#3b82f6' : '#94a3b8'
    ctx.lineWidth = isHighlighted ? 2 : 1
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke()

    // Relation label on hover
    if (isHighlighted && link.label) {
      const mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2
      ctx.globalAlpha = 1
      const tw = ctx.measureText(link.label).width + 10
      ctx.fillStyle = 'rgba(255,255,255,0.92)'
      ctx.fillRect(mx - tw / 2, my - 9, tw, 16)
      ctx.strokeStyle = '#cbd5e1'
      ctx.lineWidth = 0.5
      ctx.strokeRect(mx - tw / 2, my - 9, tw, 16)
      ctx.fillStyle = '#3b82f6'
      ctx.font = 'bold 9px Sans-Serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(link.label, mx, my)
    }
    ctx.globalAlpha = 1
  }, [hoverNode])

  return (
    <div className="flex flex-col h-full gap-2">
      <div ref={containerRef} className="flex-1 min-h-0 rounded-xl overflow-hidden border bg-slate-50">
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={{ nodes, links }}
          nodeLabel={(n: any) => `${n.label}${n.sublabel ? ` (${n.sublabel})` : ''}`}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const r = node.isCenter ? 40 : 28
            ctx.fillStyle = color
            ctx.beginPath(); ctx.arc(node.x, node.y, r, 0, 2 * Math.PI); ctx.fill()
          }}
          linkCanvasObject={linkCanvasObject}
          linkCanvasObjectMode={() => 'replace'}
          onNodeHover={(n) => setHoverNode(n ? (n as PNode) : null)}
          onNodeClick={(n) => setSelectedNode(selectedNode?.id === (n as PNode).id ? null : (n as PNode))}
          onEngineStop={() => graphRef.current?.zoomToFit(500, 60)}
          backgroundColor="#f8fafc"
          cooldownTicks={120}
        />
      </div>
      {selectedNode && (
        <div className="flex-shrink-0 rounded-lg border bg-white px-3 py-2 text-sm flex items-center gap-2">
          <span className="font-semibold">{selectedNode.label}</span>
          {selectedNode.sublabel && <Badge variant="outline">{selectedNode.sublabel}</Badge>}
          <span className="text-muted-foreground text-xs">{selectedNode.gender}</span>
        </div>
      )}
    </div>
  )
}

// ── Personal Details Card ─────────────────────────────────────────────────────
function PersonalDetailsView({ data, mainPerson }: { data: Record<string, string>; mainPerson: string }) {
  const fields = [
    { key: 'name', label: 'Name' },
    { key: 'alias', label: 'Alias / Nick Name' },
    { key: 'age', label: 'Age' },
    { key: 'dob', label: 'Date of Birth' },
    { key: 'gender', label: 'Gender' },
    { key: 'marital_status', label: 'Marital Status' },
    { key: 'occupation', label: 'Occupation' },
    { key: 'education', label: 'Education' },
    { key: 'address', label: 'Address' },
    { key: 'mobile', label: 'Mobile' },
    { key: 'email', label: 'Email' },
    { key: 'nationality', label: 'Nationality / Religion' },
    { key: 'role', label: 'Role in Case' },
    { key: 'case_no', label: 'Case / FIR No.' },
    { key: 'crime', label: 'Crime / Offence' },
  ]

  const hasData = fields.some((f) => data[f.key])

  if (!hasData) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        No personal details found in this document.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4 overflow-y-auto">
      {fields.filter((f) => data[f.key]).map((f) => (
        <div key={f.key} className="rounded-lg border bg-white p-3">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">{f.label}</p>
          <p className="text-sm font-semibold text-foreground">{data[f.key]}</p>
        </div>
      ))}
    </div>
  )
}

// ── Main Modal ────────────────────────────────────────────────────────────────
interface ProfileGraphModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceId: string
  sourceTitle?: string
  sourceImageUrl?: string
}

export function ProfileGraphModal({ open, onOpenChange, sourceId, sourceTitle, sourceImageUrl }: ProfileGraphModalProps) {
  const [data, setData] = useState<ProfileGraphData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('personal')

  useEffect(() => {
    if (!open || !sourceId) return
    setLoading(true)
    setError(null)
    sourcesApi.getProfileGraph(sourceId)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e?.response?.data?.detail || e?.message || 'Failed to load'); setLoading(false) })
  }, [open, sourceId])

  useEffect(() => {
    if (!open) { setData(null); setActiveTab('personal') }
  }, [open])

  // Build family graph
  const familyGraph = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const mainName = data.main_person || data.source_title
    const centerNode: PNode = {
      id: 'center',
      label: mainName,
      sublabel: data.personal?.role || 'main',
      gender: data.personal?.gender?.toLowerCase().includes('female') ? 'female' : 'male',
      isCenter: true,
      imageUrl: sourceImageUrl,
    }
    const nodes: PNode[] = [centerNode]
    const links: PLink[] = []
    data.family.forEach((p, i) => {
      const nid = `family:${i}`
      nodes.push({ id: nid, label: p.name, sublabel: p.relation, gender: p.gender, isCenter: false })
      links.push({ source: 'center', target: nid, label: p.relation })
    })
    return { nodes, links }
  }, [data, sourceImageUrl])

  // Build associates graph
  const associatesGraph = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const mainName = data.main_person || data.source_title
    const centerNode: PNode = {
      id: 'center',
      label: mainName,
      sublabel: data.personal?.role || 'main',
      gender: data.personal?.gender?.toLowerCase().includes('female') ? 'female' : 'male',
      isCenter: true,
      imageUrl: sourceImageUrl,
    }
    const nodes: PNode[] = [centerNode]
    const links: PLink[] = []
    data.associates.forEach((p, i) => {
      const nid = `assoc:${i}`
      nodes.push({ id: nid, label: p.name, sublabel: p.relation, gender: p.gender, isCenter: false })
      links.push({ source: 'center', target: nid, label: p.relation })
    })
    return { nodes, links }
  }, [data, sourceImageUrl])

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
        <DialogHeader className="flex-shrink-0 px-6 pt-4 pb-3 border-b">
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile Graph — {sourceTitle || 'Source'}
            {data && (
              <>
                <Badge variant="outline" className="text-blue-600 border-blue-300">
                  {data.main_person || 'Unknown'}
                </Badge>
                {data.family.length > 0 && (
                  <Badge variant="outline" className="text-green-600 border-green-300">
                    {data.family.length} family
                  </Badge>
                )}
                {data.associates.length > 0 && (
                  <Badge variant="outline" className="text-amber-600 border-amber-300">
                    {data.associates.length} associates
                  </Badge>
                )}
              </>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-hidden">
          {loading ? (
            <div className="flex h-full items-center justify-center gap-3">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
              <span className="text-muted-foreground">Extracting profile data…</span>
            </div>
          ) : error ? (
            <div className="flex h-full items-center justify-center">
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>
            </div>
          ) : data ? (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <TabsList className="mx-6 mt-3 flex-shrink-0">
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

              <TabsContent value="personal" className="flex-1 min-h-0 overflow-y-auto mx-6 mt-3">
                <PersonalDetailsView data={data.personal} mainPerson={data.main_person} />
              </TabsContent>

              <TabsContent value="family" className="flex-1 min-h-0 p-4">
                {data.family.length > 0 ? (
                  <AvatarGraph nodes={familyGraph.nodes} links={familyGraph.links} centerImageUrl={sourceImageUrl} />
                ) : (
                  <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
                    No family members found in this document.
                  </div>
                )}
              </TabsContent>

              <TabsContent value="associates" className="flex-1 min-h-0 p-4">
                {data.associates.length > 0 ? (
                  <AvatarGraph nodes={associatesGraph.nodes} links={associatesGraph.links} centerImageUrl={sourceImageUrl} />
                ) : (
                  <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
                    No friends or associates found in this document.
                  </div>
                )}
              </TabsContent>
            </Tabs>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
