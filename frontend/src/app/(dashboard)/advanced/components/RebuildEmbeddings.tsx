'use client'

import { useState, useEffect, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Loader2, AlertCircle, CheckCircle2, XCircle, Clock } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { embeddingApi } from '@/lib/api/embedding'
import type { RebuildEmbeddingsRequest, RebuildStatusResponse } from '@/lib/api/embedding'

export function RebuildEmbeddings() {
  const [mode, setMode] = useState<'existing' | 'all'>('existing')
  const [includeSources, setIncludeSources] = useState(true)
  const [includeNotes, setIncludeNotes] = useState(true)
  const [includeInsights, setIncludeInsights] = useState(true)
  const [commandId, setCommandId] = useState<string | null>(null)
  const [status, setStatus] = useState<RebuildStatusResponse | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // Rebuild mutation
  const rebuildMutation = useMutation({
    mutationFn: async (request: RebuildEmbeddingsRequest) => {
      return embeddingApi.rebuildEmbeddings(request)
    },
    onSuccess: (data) => {
      setCommandId(data.command_id)
      // Start polling for status
      startPolling(data.command_id)
    }
  })

  // Start polling for rebuild status
  const startPolling = (cmdId: string) => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }

    const interval = setInterval(async () => {
      try {
        const statusData = await embeddingApi.getRebuildStatus(cmdId)
        setStatus(statusData)

        // Stop polling if completed or failed
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          stopPolling()
        }
      } catch (error) {
        console.error('Failed to fetch rebuild status:', error)
      }
    }, 5000) // Poll every 5 seconds

    setPollingInterval(interval)
  }

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }, [pollingInterval])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  const handleStartRebuild = () => {
    const request: RebuildEmbeddingsRequest = {
      mode,
      include_sources: includeSources,
      include_notes: includeNotes,
      include_insights: includeInsights
    }

    rebuildMutation.mutate(request)
  }

  const handleReset = () => {
    stopPolling()
    setCommandId(null)
    setStatus(null)
    rebuildMutation.reset()
  }

  const isAnyTypeSelected = includeSources || includeNotes || includeInsights
  const isRebuildActive = commandId && status && (status.status === 'queued' || status.status === 'running')

  const progressData = status?.progress
  const stats = status?.stats

  const totalItems = progressData?.total_items ?? progressData?.total ?? 0
  const processedItems = progressData?.processed_items ?? progressData?.processed ?? 0
  const derivedProgressPercent = progressData?.percentage ?? (totalItems > 0 ? (processedItems / totalItems) * 100 : 0)
  const progressPercent = Number.isFinite(derivedProgressPercent) ? derivedProgressPercent : 0

  const sourcesProcessed = stats?.sources_processed ?? stats?.sources ?? 0
  const notesProcessed = stats?.notes_processed ?? stats?.notes ?? 0
  const insightsProcessed = stats?.insights_processed ?? stats?.insights ?? 0
  const failedItems = stats?.failed_items ?? stats?.failed ?? 0

  const computedDuration = status?.started_at && status?.completed_at
    ? (new Date(status.completed_at).getTime() - new Date(status.started_at).getTime()) / 1000
    : undefined
  const processingTimeSeconds = stats?.processing_time ?? computedDuration

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🔄 Rebuild Embeddings
        </CardTitle>
        <CardDescription>
          Rebuild vector embeddings for your content. Use this when switching embedding models or fixing corrupted embeddings.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration Form */}
        {!isRebuildActive && (
          <div className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="mode">Rebuild Mode</Label>
              <Select value={mode} onValueChange={(value) => setMode(value as 'existing' | 'all')}>
                <SelectTrigger id="mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="existing">Existing</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                {mode === 'existing'
                  ? 'Re-embed only items that already have embeddings (faster, for model switching)'
                  : 'Re-embed existing items + create embeddings for items without any (slower, comprehensive)'}
              </p>
            </div>

            <div className="space-y-3">
              <Label>Include in Rebuild</Label>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="sources"
                    checked={includeSources}
                    onCheckedChange={(checked) => setIncludeSources(checked === true)}
                  />
                  <Label htmlFor="sources" className="font-normal cursor-pointer">
                    Sources
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="notes"
                    checked={includeNotes}
                    onCheckedChange={(checked) => setIncludeNotes(checked === true)}
                  />
                  <Label htmlFor="notes" className="font-normal cursor-pointer">
                    Notes
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="insights"
                    checked={includeInsights}
                    onCheckedChange={(checked) => setIncludeInsights(checked === true)}
                  />
                  <Label htmlFor="insights" className="font-normal cursor-pointer">
                    Insights
                  </Label>
                </div>
              </div>
              {!isAnyTypeSelected && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please select at least one item type to rebuild
                  </AlertDescription>
                </Alert>
              )}
            </div>

            <Button
              onClick={handleStartRebuild}
              disabled={!isAnyTypeSelected || rebuildMutation.isPending}
              className="w-full"
            >
              {rebuildMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting Rebuild...
                </>
              ) : (
                '🚀 Start Rebuild'
              )}
            </Button>

            {rebuildMutation.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to start rebuild: {(rebuildMutation.error as Error)?.message || 'Unknown error'}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Status Display */}
        {status && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {status.status === 'queued' && <Clock className="h-5 w-5 text-yellow-500" />}
                {status.status === 'running' && <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />}
                {status.status === 'completed' && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                {status.status === 'failed' && <XCircle className="h-5 w-5 text-red-500" />}
                <div className="flex flex-col">
                  <span className="font-medium">
                    {status.status === 'queued' && 'Queued'}
                    {status.status === 'running' && 'Running...'}
                    {status.status === 'completed' && 'Completed!'}
                    {status.status === 'failed' && 'Failed'}
                  </span>
                  {status.status === 'running' && (
                    <span className="text-sm text-muted-foreground">
                      You can leave this page as this will run in the background
                    </span>
                  )}
                </div>
              </div>
              {(status.status === 'completed' || status.status === 'failed') && (
                <Button variant="outline" size="sm" onClick={handleReset}>
                  Start New Rebuild
                </Button>
              )}
            </div>

            {progressData && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span className="font-medium">
                    {processedItems}/{totalItems} items ({progressPercent.toFixed(1)}%)
                  </span>
                </div>
                <Progress value={progressPercent} className="h-2" />
                {failedItems > 0 && (
                  <p className="text-sm text-yellow-600">
                    ⚠️ {failedItems} items failed to process
                  </p>
                )}
              </div>
            )}

            {stats && (
              <div className="grid grid-cols-4 gap-4">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Sources</p>
                  <p className="text-2xl font-bold">{sourcesProcessed}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Notes</p>
                  <p className="text-2xl font-bold">{notesProcessed}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Insights</p>
                  <p className="text-2xl font-bold">{insightsProcessed}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Time</p>
                  <p className="text-2xl font-bold">
                    {processingTimeSeconds !== undefined ? `${processingTimeSeconds.toFixed(1)}s` : '—'}
                  </p>
                </div>
              </div>
            )}

            {status.error_message && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{status.error_message}</AlertDescription>
              </Alert>
            )}

            {status.started_at && (
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Started: {new Date(status.started_at).toLocaleString()}</p>
                {status.completed_at && (
                  <p>Completed: {new Date(status.completed_at).toLocaleString()}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Help Section */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="when">
            <AccordionTrigger>When should I rebuild embeddings?</AccordionTrigger>
            <AccordionContent className="space-y-2 text-sm">
              <p><strong>You should rebuild embeddings when:</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li><strong>Switching embedding models:</strong> If you change from one embedding model to another, you need to rebuild all embeddings to ensure consistency.</li>
                <li><strong>Upgrading model versions:</strong> When updating to a newer version of your embedding model, rebuild to take advantage of improvements.</li>
                <li><strong>Fixing corrupted embeddings:</strong> If you suspect some embeddings are corrupted or missing, rebuilding can restore them.</li>
                <li><strong>After bulk imports:</strong> If you imported content without embeddings, use &quot;All&quot; mode to embed everything.</li>
              </ul>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="time">
            <AccordionTrigger>How long does rebuilding take?</AccordionTrigger>
            <AccordionContent className="space-y-2 text-sm">
              <p><strong>Processing time depends on:</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Number of items to process</li>
                <li>Embedding model speed</li>
                <li>API rate limits (for cloud providers)</li>
                <li>System resources</li>
              </ul>
              <p className="mt-2"><strong>Typical rates:</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li><strong>Local models</strong> (Ollama): Very fast, limited only by hardware</li>
                <li><strong>Cloud APIs</strong> (OpenAI, Google): Moderate speed, may hit rate limits with large datasets</li>
                <li><strong>Sources:</strong> Slower than notes/insights (creates multiple chunks per source)</li>
              </ul>
              <p className="mt-2"><em>Example: Rebuilding 200 items might take 2-5 minutes with cloud APIs, or under 1 minute with local models.</em></p>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="safe">
            <AccordionTrigger>Is it safe to rebuild while using the app?</AccordionTrigger>
            <AccordionContent className="space-y-2 text-sm">
              <p><strong>Yes, rebuilding is safe!</strong> The rebuild process:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>✅ <strong>Is idempotent:</strong> Running multiple times produces the same result</li>
                <li>✅ <strong>Doesn&apos;t delete content:</strong> Only replaces embeddings</li>
                <li>✅ <strong>Can be run anytime:</strong> No need to stop other operations</li>
                <li>✅ <strong>Handles errors gracefully:</strong> Failed items are logged and skipped</li>
              </ul>
              <p className="mt-2">⚠️ <strong>However:</strong> Very large rebuilds (1000s of items) may temporarily slow down searches while processing.</p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}
