'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  ArrowLeft, 
  FileText, 
  Link as LinkIcon, 
  Upload, 
  AlignLeft,
  Clock,
  Hash,
  ExternalLink,
  Download,
  Copy,
  CheckCircle
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'

export default function SourceDetailPage() {
  const [source, setSource] = useState<SourceListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const router = useRouter()
  const params = useParams()
  const sourceId = params.id as string

  useEffect(() => {
    if (sourceId) {
      fetchSource()
    }
  }, [sourceId])

  // ESC key handler
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        router.push('/sources')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [router])

  const fetchSource = async () => {
    try {
      setLoading(true)
      const data = await sourcesApi.get(sourceId)
      setSource(data)
    } catch (err) {
      console.error('Failed to fetch source:', err)
      setError('Failed to load source details')
    } finally {
      setLoading(false)
    }
  }

  const getSourceIcon = () => {
    if (!source) return null
    if (source.asset?.url) return <LinkIcon className="h-5 w-5" />
    if (source.asset?.file_path) return <Upload className="h-5 w-5" />
    return <AlignLeft className="h-5 w-5" />
  }

  const getSourceType = () => {
    if (!source) return 'unknown'
    if (source.asset?.url) return 'link'
    if (source.asset?.file_path) return 'file'
    return 'text'
  }

  const handleCopyUrl = useCallback(() => {
    if (source?.asset?.url) {
      navigator.clipboard.writeText(source.asset.url)
      setCopied(true)
      toast.success('URL copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    }
  }, [source])

  const handleOpenExternal = useCallback(() => {
    if (source?.asset?.url) {
      window.open(source.asset.url, '_blank')
    }
  }, [source])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (error || !source) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error || 'Source not found'}</p>
        <Button onClick={() => router.push('/sources')}>
          Back to Sources
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push('/sources')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Sources
        </Button>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold">
              {source.title || 'Untitled Source'}
            </h1>
            <p className="mt-2 text-muted-foreground">
              Source ID: {source.id}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {getSourceIcon()}
            <Badge variant="secondary" className="text-sm">
              {getSourceType()}
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Tabs defaultValue="details" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="metadata">Metadata</TabsTrigger>
            </TabsList>
            
            <TabsContent value="details" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Source Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {source.asset?.url && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">URL</h3>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 rounded bg-muted px-2 py-1 text-sm">
                          {source.asset.url}
                        </code>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleCopyUrl}
                        >
                          {copied ? (
                            <CheckCircle className="h-4 w-4" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleOpenExternal}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                  
                  {source.asset?.file_path && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">File Path</h3>
                      <code className="rounded bg-muted px-2 py-1 text-sm">
                        {source.asset.file_path}
                      </code>
                    </div>
                  )}
                  
                  {source.topics && source.topics.length > 0 && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">Topics</h3>
                      <div className="flex flex-wrap gap-2">
                        {source.topics.map((topic, idx) => (
                          <Badge key={idx} variant="outline">
                            {topic}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="metadata" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <h3 className="mb-1 text-sm font-semibold">Created</h3>
                      <p className="text-sm text-muted-foreground">
                        {new Date(source.created).toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(source.created), { addSuffix: true })}
                      </p>
                    </div>
                    <div>
                      <h3 className="mb-1 text-sm font-semibold">Updated</h3>
                      <p className="text-sm text-muted-foreground">
                        {new Date(source.updated).toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(source.updated), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Embedded Chunks</span>
                </div>
                <span className="font-semibold">{source.embedded_chunks || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Insights</span>
                </div>
                <span className="font-semibold">{source.insights_count || 0}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {source.asset?.file_path && (
                <Button variant="outline" className="w-full" disabled>
                  <Download className="mr-2 h-4 w-4" />
                  Download File
                </Button>
              )}
              <Button
                variant="destructive"
                className="w-full"
                onClick={async () => {
                  if (confirm('Are you sure you want to delete this source?')) {
                    try {
                      await sourcesApi.delete(source.id)
                      toast.success('Source deleted successfully')
                      router.push('/sources')
                    } catch (err) {
                      toast.error('Failed to delete source')
                    }
                  }
                }}
              >
                Delete Source
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}