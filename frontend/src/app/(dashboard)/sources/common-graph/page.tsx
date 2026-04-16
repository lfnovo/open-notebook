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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type CommonGraphNode = {
  id: string
  label: string
  type: 'source' | 'term'
  weight?: number
}

type CommonGraphLink = {
  source: string
  target: string
  weight?: number
}

type CommonGraphVisualization = {
  nodes: CommonGraphNode[]
  links: CommonGraphLink[]
}

function CommonGraphViewer({ graph }: { graph: CommonGraphVisualization }) {
  const graphRef = useRef<ForceGraphMethods | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 520 })
  const [hoverNode, setHoverNode] = useState<CommonGraphNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<CommonGraphNode | null>(null)

  const hoveredLinkIds = useMemo(() => {
    if (!hoverNode) {
      return new Set<string>()
    }
    return new Set(
      graph.links
        .filter(
          (link) => link.source === hoverNode.id || link.target === hoverNode.id
        )
        .map((link) => `${link.source}--${link.target}`)
    )
  }, [graph.links, hoverNode])

  useEffect(() => {
    const current = containerRef.current
    if (!current) {
      return
    }

    const observer = new ResizeObserver((entries) => {
      const rect = entries[0].contentRect
      setDimensions({
        width: Math.max(600, Math.round(rect.width)),
        height: Math.max(480, Math.round(rect.height)),
      })
    })

    observer.observe(current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const fg = graphRef.current
    if (!fg) {
      return
    }

    fg.d3Force('charge')?.strength(-300)
    fg.d3Force('link')?.distance(80)
    fg.d3Force('center')?.x(dimensions.width / 2).y(dimensions.height / 2)
  }, [dimensions])

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSource = node.type === 'source'
      const radius = isSource
        ? 18
        : Math.min(6 + (node.weight ?? 1) / 4, 20)
      const label = node.label || ''

      ctx.globalAlpha = hoverNode && hoverNode.id !== node.id ? 0.15 : 1
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
      ctx.fillStyle = isSource ? '#1D6FAE' : '#1D9E75'
      ctx.fill()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.textBaseline = isSource || radius >= 12 ? 'middle' : 'top'
      ctx.font = `${isSource ? 12 : 10}px Sans-Serif`
      const displayedLabel = label.length > 14 ? `${label.slice(0, 12)}…` : label
      const textY = isSource || radius >= 12 ? node.y : node.y + radius + 4
      ctx.fillText(displayedLabel, node.x, textY)
      ctx.globalAlpha = 1
    },
    [hoverNode]
  )

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mt-4">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm font-semibold">Common graph visualization</div>
        <button
          type="button"
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => graphRef.current?.zoomToFit(400)}
        >
          Fit to screen
        </button>
      </div>

      <div
        ref={containerRef}
        className="relative min-h-[520px] overflow-hidden rounded-lg border border-slate-200 bg-white"
      >
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graph}
          nodeLabel={(node: any) => `${node.label}${node.weight ? ` (${node.weight})` : ''}`}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(node.x, node.y, node.type === 'source' ? 18 : Math.min(6 + (node.weight ?? 1) / 4, 20), 0, 2 * Math.PI)
            ctx.fill()
          }}
          linkWidth={(link: any) => Math.max(1, (link.weight ?? 1) / 5)}
          linkColor={(link: any) => {
            if (!hoverNode) {
              return 'rgba(100,100,100,0.3)'
            }
            return hoveredLinkIds.has(`${link.source}--${link.target}`)
              ? 'rgba(100,100,100,0.8)'
              : 'rgba(100,100,100,0.08)'
          }}
          linkDirectionalParticles={0}
          onNodeHover={(node) => setHoverNode(node ? (node as CommonGraphNode) : null)}
          onNodeClick={(node) => setSelectedNode(node as CommonGraphNode)}
          onEngineStop={() => graphRef.current?.zoomToFit(400)}
          dagMode={undefined}
        />
      </div>

      <div className="mt-4 flex flex-col gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-900 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-3 w-3 rounded-full bg-[#1D6FAE]" />
            <span>Source document</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-3 w-3 rounded-full bg-[#1D9E75]" />
            <span>Common term (size = frequency)</span>
          </div>
        </div>
        {selectedNode ? (
          <div className="rounded-md border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Selected node</p>
            <p className="mt-2 font-semibold text-slate-900">{selectedNode.label}</p>
            <p className="text-xs text-slate-500">Type: {selectedNode.type}</p>
            {selectedNode.weight !== undefined && (
              <p className="text-xs text-slate-500">Weight: {selectedNode.weight}</p>
            )}
          </div>
        ) : (
          <div className="rounded-md border border-slate-200 bg-white p-3 text-slate-600">
            Hover or click a node to inspect it.
          </div>
        )}
      </div>
    </div>
  )
}

export default function CommonGraphPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const idsParam = searchParams?.get('ids') ?? ''
  const sourceIds = useMemo(
    () => idsParam.split(',').filter(Boolean).map((id) => decodeURIComponent(id)),
    [idsParam]
  )

  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [buildStatus, setBuildStatus] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const [buildResult, setBuildResult] = useState<CommonGraphResponse | null>(null)
  const [isBuilding, setIsBuilding] = useState(false)

  const graphData = useMemo(() => {
    const rawMetadata = buildResult?.metadata as any
    return rawMetadata?.graph ? (rawMetadata.graph as CommonGraphVisualization) : undefined
  }, [buildResult])

  const [graphOpen, setGraphOpen] = useState(false)

  const commonTerms = useMemo(() => {
    const rawMetadata = buildResult?.metadata as any
    return rawMetadata?.common_terms as string[] | undefined
  }, [buildResult])

  const graphHasContent = Boolean(graphData?.nodes?.length && graphData?.links?.length)

  useEffect(() => {
    let isActive = true
    if (sourceIds.length === 0) {
      setSources([])
      setLoading(false)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    setBuildStatus(null)

    Promise.all(sourceIds.map((id) => sourcesApi.get(id).catch(() => null)))
      .then((results) => {
        if (!isActive) return
        setSources(results.filter(Boolean) as SourceListResponse[])
      })
      .catch((err) => {
        if (!isActive) return
        setError('Failed to load selected sources.')
      })
      .finally(() => {
        if (!isActive) return
        setLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [sourceIds])

  const invalidIds = useMemo(
    () => sourceIds.filter((id) => !sources.some((source) => source.id === id)),
    [sourceIds, sources]
  )
  const canBuild = sources.length >= 2 && invalidIds.length === 0

  const handleBuild = async () => {
    if (!canBuild || isBuilding) {
      return
    }

    setBuildError(null)
    setBuildStatus('Building common graph...')
    setIsBuilding(true)

    try {
      const result = await sourcesApi.createCommonGraph({
        source_ids: sourceIds,
      })
      setBuildResult(result)
      setBuildStatus('Common graph generation started and saved.')

      if (result.id) {
        const savedGraph = await sourcesApi.getCommonGraph(result.id)
        setBuildResult(savedGraph)
      }
    } catch (error) {
      console.error(error)

      const axiosError = error as AxiosError | undefined
      const detail =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        (error instanceof Error ? error.message : null)

      setBuildError(detail ?? 'Failed to create common graph. Please try again.')
      setBuildStatus(null)
    } finally {
      setIsBuilding(false)
    }
  }

  return (
    <AppShell>
      <div className="flex flex-col h-full w-full px-6 py-6">
        <div className="mb-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold">Create common graph</h1>
              <p className="mt-2 text-muted-foreground max-w-2xl">
                Use this page to review the sources selected for a shared graph and build a common
                analysis view. At least two selected sources are required.
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push('/sources')}>
              Back to sources
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.75fr_1fr]">
          <Card className="space-y-4">
            <CardHeader>
              <CardTitle className="text-lg">Selected sources</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading selected sources…</p>
              ) : error ? (
                <p className="text-sm text-red-500">{error}</p>
              ) : sourceIds.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No source IDs were provided. Return to the sources list and select at least two
                  items.
                </p>
              ) : (
                <div className="space-y-3">
                  {sources.map((source) => (
                    <div
                      key={source.id}
                      className="rounded-xl border p-4 bg-background"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="font-semibold">{source.title || 'Untitled source'}</p>
                          <p className="text-sm text-muted-foreground truncate">
                            {source.asset?.url || source.asset?.file_path || 'Source content'}
                          </p>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {source.embedded ? 'Embedded' : 'Not embedded'}
                        </Badge>
                      </div>
                    </div>
                  ))}

                  {invalidIds.length > 0 && (
                    <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4">
                      <p className="text-sm font-semibold text-destructive">
                        Some source IDs could not be loaded:
                      </p>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-destructive">
                        {invalidIds.map((id) => (
                          <li key={id}>{id}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="space-y-4">
            <CardHeader>
              <CardTitle className="text-lg">Common graph status</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {sources.length > 0
                  ? `${sources.length} selected source${sources.length === 1 ? '' : 's'}`
                  : 'Select at least two sources from the source list to enable the graph action.'}
              </p>
              <Button
                className="w-full"
                disabled={!canBuild || isBuilding}
                onClick={handleBuild}
              >
                {isBuilding ? 'Building common graph…' : 'Build common graph'}
              </Button>
              {invalidIds.length > 0 && (
                <p className="mt-3 text-sm text-destructive">
                  Resolve invalid selections before building the graph.
                </p>
              )}
              {buildStatus && (
                <div className="rounded-xl border border-green-200 bg-green-50 p-4 mt-4 text-sm text-green-900">
                  {buildStatus}
                </div>
              )}
              {buildError && (
                <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 mt-4 text-sm text-destructive">
                  {buildError}
                </div>
              )}
              {buildResult && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mt-4 text-sm text-slate-900">
                  <p className="font-medium">Saved common graph</p>
                  <p>ID: {buildResult.id}</p>
                  <p>Sources: {buildResult.source_ids.length}</p>
                  {buildResult.title && <p>Title: {buildResult.title}</p>}
                  {graphHasContent && (
                    <Button
                      className="mt-4 w-full"
                      onClick={() => setGraphOpen(true)}
                    >
                      View full-screen graph
                    </Button>
                  )}
                </div>
              )}
              {graphData && !graphHasContent && (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">Graph contains insufficient data to render.</p>
                  <p className="mt-2">The common graph was saved, but the metadata did not produce an interactive graph.</p>
                </div>
              )}
              {graphData && commonTerms && commonTerms.length > 0 && (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-900">
                  <p className="font-semibold">Common terms detected</p>
                  <p className="mt-2 text-sm">{commonTerms.join(', ')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Dialog open={graphOpen} onOpenChange={setGraphOpen}>
          <DialogContent className="w-[min(95vw,1200px)] max-h-[95vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle>Common graph visualization</DialogTitle>
            </DialogHeader>
            <div className="mt-4 h-[80vh] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
              {graphHasContent ? (
                <CommonGraphViewer graph={graphData as CommonGraphVisualization} />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  Graph data is not available for visualization.
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  )
}
