'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Clock, Hash, Link as LinkIcon, Upload, AlignLeft } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchSources()
  }, [])

  const fetchSources = async () => {
    try {
      setLoading(true)
      const data = await sourcesApi.list()
      setSources(data)
    } catch (err) {
      console.error('Failed to fetch sources:', err)
      setError('Failed to load sources')
    } finally {
      setLoading(false)
    }
  }

  const getSourceIcon = (source: SourceListResponse) => {
    if (source.asset?.url) return <LinkIcon className="h-5 w-5" />
    if (source.asset?.file_path) return <Upload className="h-5 w-5" />
    return <AlignLeft className="h-5 w-5" />
  }

  const getSourceType = (source: SourceListResponse) => {
    if (source.asset?.url) return 'link'
    if (source.asset?.file_path) return 'file'
    return 'text'
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  if (sources.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-12 w-12" />}
        title="No sources yet"
        description="Sources from all notebooks will appear here"
      />
    )
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">All Sources</h1>
        <p className="mt-2 text-muted-foreground">
          Browse all sources across your notebooks
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <Card
            key={source.id}
            className="cursor-pointer transition-colors hover:bg-accent"
            onClick={() => router.push(`/sources/${source.id}`)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  {getSourceIcon(source)}
                  <Badge variant="secondary">{getSourceType(source)}</Badge>
                </div>
              </div>
              <CardTitle className="mt-2 line-clamp-2">
                {source.title || 'Untitled Source'}
              </CardTitle>
              {source.asset?.url && (
                <CardDescription className="line-clamp-1 text-xs">
                  {source.asset.url}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-2 text-sm text-muted-foreground">
                {source.topics && source.topics.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {source.topics.slice(0, 3).map((topic, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {topic}
                      </Badge>
                    ))}
                    {source.topics.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{source.topics.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <Hash className="h-3 w-3" />
                    <span>{source.embedded_chunks || 0} chunks</span>
                  </div>
                  {source.insights_count > 0 && (
                    <div className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      <span>{source.insights_count} insights</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>
                    {formatDistanceToNow(new Date(source.created), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}