'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceDetailResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
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
  CheckCircle,
  Youtube,
  Bot
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'

export default function SourceDetailPage() {
  const [source, setSource] = useState<SourceDetailResponse | null>(null)
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

  // Extract YouTube video ID from URL
  const getYouTubeVideoId = (url: string): string | null => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/watch\?.*v=([^&\n?#]+)/
    ]
    
    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1]
    }
    return null
  }

  const isYouTubeUrl = useMemo(() => {
    if (!source?.asset?.url) return false
    return !!(getYouTubeVideoId(source.asset.url))
  }, [source?.asset?.url])

  const youTubeVideoId = useMemo(() => {
    if (!source?.asset?.url) return null
    return getYouTubeVideoId(source.asset.url)
  }, [source?.asset?.url])

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

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-2">
          <Tabs defaultValue="content" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="details">Details</TabsTrigger>
            </TabsList>
            
            <TabsContent value="content" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {isYouTubeUrl && <Youtube className="h-5 w-5" />}
                    Content
                  </CardTitle>
                  {source.asset?.url && !isYouTubeUrl && (
                    <CardDescription className="flex items-center gap-2">
                      <LinkIcon className="h-4 w-4" />
                      <a 
                        href={source.asset.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="hover:underline text-blue-600"
                      >
                        {source.asset.url}
                      </a>
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  {isYouTubeUrl && youTubeVideoId && (
                    <div className="mb-6">
                      <div className="aspect-video rounded-lg overflow-hidden bg-black">
                        <iframe
                          src={`https://www.youtube.com/embed/${youTubeVideoId}`}
                          title="YouTube video"
                          className="w-full h-full"
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowFullScreen
                        />
                      </div>
                      <div className="mt-2">
                        <a 
                          href={source.asset.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-sm text-muted-foreground hover:underline inline-flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Open on YouTube
                        </a>
                      </div>
                    </div>
                  )}
                  <ScrollArea className="h-[600px] w-full pr-4">
                    <div className="prose prose-neutral dark:prose-invert max-w-none">
                      <ReactMarkdown>
                        {source.full_text || 'No content available'}
                      </ReactMarkdown>
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="details" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Source Information */}
                  <div className="space-y-4">
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
                  </div>

                  {/* Statistics */}
                  <div>
                    <h3 className="mb-3 text-sm font-semibold">Statistics</h3>
                    <div className="space-y-2 rounded-lg bg-muted/50 p-3">
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
                    </div>
                  </div>

                  {/* Metadata */}
                  <div>
                    <h3 className="mb-3 text-sm font-semibold">Metadata</h3>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium text-muted-foreground">Created</p>
                        <p className="text-sm">
                          {formatDistanceToNow(new Date(source.created), { addSuffix: true })}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(source.created).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-muted-foreground">Updated</p>
                        <p className="text-sm">
                          {formatDistanceToNow(new Date(source.updated), { addSuffix: true })}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(source.updated).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {/* Actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-2">
              {source.asset?.file_path && (
                <Button variant="outline" size="sm" disabled>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              )}
              <Button
                variant="destructive"
                size="sm"
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

          {/* Chat Placeholder */}
          <Card className="flex-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Chat with AI
              </CardTitle>
              <CardDescription>
                Ask questions about this source
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-[500px] flex-col">
                {/* Messages Area */}
                <ScrollArea className="flex-1 rounded-lg border bg-muted/20 p-4">
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p className="text-sm">Start a conversation about this source</p>
                      <p className="text-xs mt-2">Chat functionality coming soon...</p>
                    </div>
                  </div>
                </ScrollArea>
                
                {/* Input Area */}
                <div className="mt-4 flex gap-2">
                  <input
                    type="text"
                    placeholder="Ask a question..."
                    className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
                    disabled
                  />
                  <Button size="sm" disabled>
                    Send
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}