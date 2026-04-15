'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { sourcesApi } from '@/lib/api/sources'
import { commonGraphsApi } from '@/lib/api/commonGraphs'
import { CommonGraphResponse, CreateCommonGraphRequest, SourceListResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

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
  const [saving, setSaving] = useState(false)
  const [savedGraph, setSavedGraph] = useState<CommonGraphResponse | null>(null)

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

  const handleBuildCommonGraph = async () => {
    if (!canBuild || saving) return

    setSaving(true)
    setBuildStatus(null)
    setSavedGraph(null)

    try {
      const request: CreateCommonGraphRequest = {
        source_ids: sourceIds,
        title: `Common graph for ${sources.length} sources`,
      }
      const graph = await commonGraphsApi.create(request)
      setSavedGraph(graph)
      setBuildStatus('Common graph saved to the database successfully.')
    } catch (err) {
      setBuildStatus('Failed to save the common graph. Please try again.')
    } finally {
      setSaving(false)
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
                disabled={!canBuild || saving}
                onClick={handleBuildCommonGraph}
              >
                {saving ? 'Saving common graph…' : 'Build common graph'}
              </Button>
              {savedGraph && (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 mt-4 text-sm text-blue-900">
                  <p className="font-semibold">Common graph saved</p>
                  <p>ID: {savedGraph.id}</p>
                  <p>Status: {savedGraph.status}</p>
                  {savedGraph.message && <p>{savedGraph.message}</p>}
                </div>
              )}
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
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
