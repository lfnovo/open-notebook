'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { insightsApi, SourceInsightResponse } from '@/lib/api/insights'
import { transformationsApi } from '@/lib/api/transformations'
import { embeddingApi } from '@/lib/api/embedding'
import { SourceDetailResponse } from '@/lib/types/api'
import { Transformation } from '@/lib/types/transformations'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { InlineEdit } from '@/components/common/InlineEdit'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
  Bot,
  MoreVertical,
  Trash2,
  Sparkles,
  Plus,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  Database,
  AlertCircle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { useSourceChat } from '@/lib/hooks/useSourceChat'
import { ChatPanel } from '@/components/source/ChatPanel'

export default function SourceDetailPage() {
  const [source, setSource] = useState<SourceDetailResponse | null>(null)
  const [insights, setInsights] = useState<SourceInsightResponse[]>([])
  const [transformations, setTransformations] = useState<Transformation[]>([])
  const [selectedTransformation, setSelectedTransformation] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [creatingInsight, setCreatingInsight] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [isEmbedding, setIsEmbedding] = useState(false)
  const [expandedInsights, setExpandedInsights] = useState<Set<string>>(new Set())
  const router = useRouter()
  const params = useParams()
  const sourceId = decodeURIComponent(params.id as string)

  // Initialize source chat
  const chat = useSourceChat(sourceId)

  useEffect(() => {
    if (sourceId) {
      fetchSource()
      fetchInsights()
      fetchTransformations()
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

  const fetchInsights = async () => {
    try {
      setLoadingInsights(true)
      const data = await insightsApi.listForSource(sourceId)
      setInsights(data)
    } catch (err) {
      console.error('Failed to fetch insights:', err)
    } finally {
      setLoadingInsights(false)
    }
  }

  const fetchTransformations = async () => {
    try {
      const data = await transformationsApi.list()
      setTransformations(data)
    } catch (err) {
      console.error('Failed to fetch transformations:', err)
    }
  }

  const createInsight = async () => {
    if (!selectedTransformation) {
      toast.error('Please select a transformation')
      return
    }

    try {
      setCreatingInsight(true)
      await insightsApi.create(sourceId, {
        transformation_id: selectedTransformation
      })
      toast.success('Insight created successfully')
      await fetchInsights()
      setSelectedTransformation('')
    } catch (err) {
      console.error('Failed to create insight:', err)
      toast.error('Failed to create insight')
    } finally {
      setCreatingInsight(false)
    }
  }

  const handleUpdateTitle = async (title: string) => {
    if (!source || title === source.title) return
    
    try {
      await sourcesApi.update(sourceId, { title })
      toast.success('Source title updated')
      // Update local state to reflect the change immediately
      setSource({ ...source, title })
    } catch (err) {
      console.error('Failed to update source title:', err)
      toast.error('Failed to update source title')
      // Re-fetch to ensure we have the correct data
      await fetchSource()
    }
  }

  const handleEmbedContent = async () => {
    if (!source) return
    
    try {
      setIsEmbedding(true)
      const response = await embeddingApi.embedContent(sourceId, 'source')
      toast.success(response.message)
      // Refresh source data to update embedded status
      await fetchSource()
    } catch (err) {
      console.error('Failed to embed content:', err)
      toast.error('Failed to embed content')
    } finally {
      setIsEmbedding(false)
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

  const toggleInsight = useCallback((insightId: string) => {
    setExpandedInsights(prev => {
      const newSet = new Set(prev)
      if (newSet.has(insightId)) {
        newSet.delete(insightId)
      } else {
        newSet.add(insightId)
      }
      return newSet
    })
  }, [])

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
    <div className="flex flex-col h-screen">
      <div className="pt-6 pb-4 px-6">
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
          <div className="flex-1">
            <InlineEdit
              value={source.title || ''}
              onSave={handleUpdateTitle}
              className="text-3xl font-bold"
              inputClassName="text-3xl font-bold"
              placeholder="Source title"
              emptyText="Untitled Source"
            />
            <p className="mt-2 text-muted-foreground">
              Source ID: {source.id}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {getSourceIcon()}
            <Badge variant="secondary" className="text-sm">
              {getSourceType()}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {source.asset?.file_path && (
                  <>
                    <DropdownMenuItem disabled>
                      <Download className="mr-2 h-4 w-4" />
                      Download File
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem
                  onClick={handleEmbedContent}
                  disabled={isEmbedding || source.embedded}
                >
                  <Database className="mr-2 h-4 w-4" />
                  {isEmbedding ? 'Embedding...' : source.embedded ? 'Already Embedded' : 'Embed Content'}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
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
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Source
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div className="flex-1 grid gap-6 lg:grid-cols-[2fr_1fr] overflow-hidden px-6">
        <div className="overflow-y-auto px-4 pb-6">
          <Tabs defaultValue="content" className="w-full">
            <TabsList className="grid w-full grid-cols-3 sticky top-0 z-10">
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="insights">
                Insights {insights.length > 0 && `(${insights.length})`}
              </TabsTrigger>
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
                  <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-blue-600 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-4">{children}</p>,
                        h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-4">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-3">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2">{children}</h3>,
                        ul: ({ children }) => <ul className="mb-4 list-disc pl-6">{children}</ul>,
                        ol: ({ children }) => <ol className="mb-4 list-decimal pl-6">{children}</ol>,
                        li: ({ children }) => <li className="mb-1">{children}</li>,
                      }}
                    >
                      {source.full_text || 'No content available'}
                    </ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="insights" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Lightbulb className="h-5 w-5" />
                      Insights
                    </span>
                    <Badge variant="secondary">{insights.length}</Badge>
                  </CardTitle>
                  <CardDescription>
                    AI-generated insights about this source
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Create New Insight */}
                  <div className="rounded-lg border bg-muted/30 p-4">
                    <h3 className="mb-3 text-sm font-semibold flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      Generate New Insight
                    </h3>
                    <div className="flex gap-2">
                      <Select
                        value={selectedTransformation}
                        onValueChange={setSelectedTransformation}
                        disabled={creatingInsight}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Select a transformation..." />
                        </SelectTrigger>
                        <SelectContent>
                          {transformations.map((trans) => (
                            <SelectItem key={trans.id} value={trans.id}>
                              {trans.title || trans.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        onClick={createInsight}
                        disabled={!selectedTransformation || creatingInsight}
                      >
                        {creatingInsight ? (
                          <>
                            <LoadingSpinner className="mr-2 h-3 w-3" />
                            Creating...
                          </>
                        ) : (
                          <>
                            <Plus className="mr-2 h-4 w-4" />
                            Create
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Insights List */}
                  {loadingInsights ? (
                    <div className="flex items-center justify-center py-8">
                      <LoadingSpinner />
                    </div>
                  ) : insights.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">No insights yet</p>
                      <p className="text-xs mt-1">Create your first insight using a transformation above</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {insights.map((insight) => {
                        const isExpanded = expandedInsights.has(insight.id)
                        const previewText = insight.content.slice(0, 150) + (insight.content.length > 150 ? '...' : '')
                        
                        return (
                          <div
                            key={insight.id}
                            className="rounded-lg border bg-background"
                          >
                            <div 
                              className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                              onClick={() => toggleInsight(insight.id)}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                  )}
                                  <Badge variant="outline" className="text-xs">
                                    {insight.insight_type}
                                  </Badge>
                                </div>
                                {insight.created && (
                                  <span className="text-xs text-muted-foreground">
                                    {(() => {
                                      try {
                                        const date = new Date(insight.created)
                                        if (isNaN(date.getTime())) {
                                          return 'Unknown date'
                                        }
                                        return formatDistanceToNow(date, { addSuffix: true })
                                      } catch {
                                        return 'Unknown date'
                                      }
                                    })()}
                                  </span>
                                )}
                              </div>
                              {!isExpanded && (
                                <p className="mt-2 text-sm text-muted-foreground">
                                  {previewText}
                                </p>
                              )}
                            </div>
                            {isExpanded && (
                              <div className="px-4 pb-4 border-t">
                                <div className="mt-4 prose prose-sm prose-neutral dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-blue-600 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
                                  <ReactMarkdown
                                    components={{
                                      p: ({ children }) => <p className="mb-4">{children}</p>,
                                      h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-4">{children}</h1>,
                                      h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-3">{children}</h2>,
                                      h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2">{children}</h3>,
                                      ul: ({ children }) => <ul className="mb-4 list-disc pl-6">{children}</ul>,
                                      ol: ({ children }) => <ol className="mb-4 list-decimal pl-6">{children}</ol>,
                                      li: ({ children }) => <li className="mb-1">{children}</li>,
                                    }}
                                  >
                                    {insight.content}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="details" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Embedding Alert */}
                  {!source.embedded && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>
                        Content Not Embedded
                      </AlertTitle>
                      <AlertDescription>
                        This content hasn't been embedded for vector search. Embedding enables advanced search capabilities and better content discovery.
                        <div className="mt-3">
                          <Button
                            onClick={handleEmbedContent}
                            disabled={isEmbedding}
                            size="sm"
                          >
                            <Database className="mr-2 h-4 w-4" />
                            {isEmbedding ? 'Embedding...' : 'Embed Content'}
                          </Button>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

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
                          <span className="text-sm">Embedded</span>
                        </div>
                        <Badge variant={source.embedded ? "default" : "secondary"}>
                          {source.embedded ? "Yes" : "No"}
                        </Badge>
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

        {/* Right column - Chat */}
        <div className="overflow-y-auto px-4 pb-6">
          <ChatPanel
            messages={chat.messages}
            isStreaming={chat.isStreaming}
            contextIndicators={chat.contextIndicators}
            onSendMessage={(message, model) => chat.sendMessage(message, model)}
            modelOverride={chat.currentSession?.model_override}
            onModelChange={(model) => {
              if (chat.currentSessionId) {
                chat.updateSession(chat.currentSessionId, { model_override: model })
              }
            }}
            sessions={chat.sessions}
            currentSessionId={chat.currentSessionId}
            onCreateSession={(title) => chat.createSession({ title })}
            onSelectSession={chat.switchSession}
            onUpdateSession={(sessionId, title) => chat.updateSession(sessionId, { title })}
            onDeleteSession={chat.deleteSession}
            loadingSessions={chat.loadingSessions}
          />
        </div>
      </div>
    </div>
  )
}