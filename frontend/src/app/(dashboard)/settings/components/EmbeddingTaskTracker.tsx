"use client"

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, RefreshCw, Database, AlertCircle } from 'lucide-react'
import apiClient from '@/lib/api/client'

interface EmbeddingSummary {
  total: number
  running: number
  pending: number
  completed_recently: number
  failed_recently: number
}

interface EmbeddingTasksResponse {
  tasks: unknown[]
  summary: EmbeddingSummary
}

const defaultSummary: EmbeddingSummary = {
  total: 0,
  running: 0,
  pending: 0,
  completed_recently: 0,
  failed_recently: 0,
}

async function getEmbeddingTasks(): Promise<EmbeddingTasksResponse> {
  try {
    const response = await apiClient.get<EmbeddingTasksResponse>('/commands/embedding/status')
    return response.data
  } catch (error) {
    console.error('Failed to fetch embedding tasks:', error)
    return { tasks: [], summary: defaultSummary }
  }
}

export function EmbeddingTaskTracker() {
  const { data, isLoading, refetch, isError } = useQuery({
    queryKey: ['embedding-tasks-summary'],
    queryFn: getEmbeddingTasks,
    refetchInterval: 20000,
    retry: 1,
    staleTime: 15000,
  })

  const summary = data?.summary ?? defaultSummary

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            <div>
              <CardTitle>Embedding Status</CardTitle>
              <CardDescription>Simple summary of embedding activity</CardDescription>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="text-center py-6 text-muted-foreground">
            <AlertCircle className="h-10 w-10 mx-auto mb-2 opacity-50 text-destructive" />
            <p>Unable to load embedding summary</p>
          </div>
        ) : isLoading && !data ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{summary.total}</div>
              <div className="text-xs text-muted-foreground">Total</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-blue-500/10">
              <div className="text-2xl font-bold text-blue-500">{summary.running}</div>
              <div className="text-xs text-muted-foreground">Running</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-yellow-500/10">
             <div className="text-2xl font-bold text-yellow-500">{summary.pending}</div>
              <div className="text-xs text-muted-foreground">Pending</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-green-500/10">
              <div className="text-2xl font-bold text-green-500">{summary.completed_recently}</div>
              <div className="text-xs text-muted-foreground">Completed</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-destructive/10">
              <div className="text-2xl font-bold text-destructive">{summary.failed_recently}</div>
              <div className="text-xs text-muted-foreground">Failed</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
